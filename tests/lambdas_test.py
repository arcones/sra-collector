import json

import boto3
import botocore
import pytest
from utils_test import _ensure_queue_is_empty
from utils_test import _get_all_queue_messages
from utils_test import _get_customized_input_from_sqs
from utils_test import _get_db_connection
from utils_test import _provide_random_ncbi_query
from utils_test import _provide_random_request_id
from utils_test import _store_test_request
from utils_test import _store_test_srp
from utils_test import _store_test_study
from utils_test import _wait_test_server_readiness

SQS_TEST_QUEUE = 'https://sqs.eu-central-1.amazonaws.com/120715685161/integration_test_queue'

_S_QUERY = {'query': 'stroke AND single cell rna seq AND musculus', 'results': 8}
_2XL_QUERY = {'query': 'rna seq and homo sapiens and myeloid and leukemia', 'results': 1088}


@pytest.fixture(scope='session', autouse=True)
def init_tests():
    _wait_test_server_readiness()


@pytest.fixture(scope='session', autouse=True)
def lambda_client():
    botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=90, retries={'max_attempts': 0})
    lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)
    yield lambda_client
    lambda_client.close()


@pytest.fixture(scope='session', autouse=True)
def sqs_client():
    sqs_client = boto3.client('sqs', region_name='eu-central-1')
    try:
        sqs_client.purge_queue(QueueUrl=SQS_TEST_QUEUE)
    except sqs_client.exceptions.PurgeQueueInProgress as purgeQueueActionInProgress:
        print(f'There is a purge action already in progress for test SQS')
    _ensure_queue_is_empty(sqs_client, SQS_TEST_QUEUE)
    yield sqs_client
    sqs_client.close()


@pytest.fixture(scope='session', autouse=True)
def database_holder():
    database_connection = _get_db_connection()
    database_cursor = database_connection.cursor()
    database_cursor.execute("""
        TRUNCATE TABLE sracollector_dev.sra_run cascade;
        TRUNCATE TABLE sracollector_dev.sra_project cascade;
        TRUNCATE TABLE sracollector_dev.geo_study cascade;
        TRUNCATE TABLE sracollector_dev.request cascade;
    """)
    database_connection.commit()
    yield database_cursor, database_connection
    database_cursor.close()
    database_connection.close()


def test_a_get_user_query(lambda_client, sqs_client):
    lambda_function = 'A_get_user_query'

    expected_request_id = _provide_random_request_id()
    expected_ncbi_query = _provide_random_ncbi_query()
    expected_body = json.dumps({'ncbi_query': expected_ncbi_query}).replace('"', '\"')

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['requestContext']['requestId'] = expected_request_id
        payload['body'] = expected_body
        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    assert 200 == response['StatusCode']

    actual_response = json.loads(response['Payload'].read())

    actual_response_inner_status = actual_response['statusCode']
    actual_response_payload = actual_response['body']

    assert 201 == actual_response_inner_status
    assert f'{{"request_id": "{expected_request_id}", "ncbi_query": "{expected_ncbi_query}"}}' == actual_response_payload

    messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=1)

    sqs_message = messages[0]
    sqs_message_payload = json.loads(sqs_message['Body'])

    assert expected_request_id == sqs_message_payload['request_id']
    assert expected_ncbi_query == sqs_message_payload['ncbi_query']


def test_b_get_query_pages(lambda_client, sqs_client, database_holder):
    function_name = 'B_get_query_pages'

    expected_request_id_1 = _provide_random_request_id()
    expected_request_id_2 = _provide_random_request_id()
    expected_bodies = [
        json.dumps({'request_id': expected_request_id_1, 'ncbi_query': _S_QUERY['query']}).replace('"', '\"'),
        json.dumps({'request_id': expected_request_id_2, 'ncbi_query': _2XL_QUERY['query']}).replace('"', '\"'),
    ]

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_bodies)))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder

    database_cursor.execute(f"select id, query, geo_count from sracollector_dev.request where id in ('{expected_request_id_1}', '{expected_request_id_2}')")
    actual_rows = database_cursor.fetchall()
    actual_rows = sorted(actual_rows, key=lambda row: (row[0]))

    expected_rows = [
        (expected_request_id_1, _S_QUERY['query'], _S_QUERY['results']),
        (expected_request_id_2, _2XL_QUERY['query'], _2XL_QUERY['results'])
    ]
    expected_rows = sorted(expected_rows, key=lambda row: (row[0]))

    assert expected_rows == actual_rows

    expected_message_bodies = [{'request_id': expected_request_id_1, 'ncbi_query': _S_QUERY['query'], 'retstart': 0, 'retmax': 500},
                               {'request_id': expected_request_id_2, 'ncbi_query': _2XL_QUERY['query'], 'retstart': 0, 'retmax': 500},
                               {'request_id': expected_request_id_2, 'ncbi_query': _2XL_QUERY['query'], 'retstart': 500, 'retmax': 500},
                               {'request_id': expected_request_id_2, 'ncbi_query': _2XL_QUERY['query'], 'retstart': 1000, 'retmax': 500}]

    expected_message_bodies = sorted(expected_message_bodies, key=lambda message: (message['request_id'], message['retstart']))

    actual_messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_message_bodies))
    actual_message_bodies = [json.loads(message['Body']) for message in actual_messages]
    actual_message_bodies = sorted(actual_message_bodies, key=lambda message: (message['request_id'], message['retstart']))

    assert expected_message_bodies == actual_message_bodies


def test_c_get_study_ids(lambda_client, sqs_client):
    function_name = 'C_get_study_ids'

    expected_request_id = _provide_random_request_id()
    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': _S_QUERY['query'], 'retstart': 0, 'retmax': 500}).replace('"', '\"')

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_body)))

    assert 200 == response['StatusCode']

    messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=8)

    messages_body = [json.loads(message['Body']) for message in messages]
    request_id = {body['request_info']['request_id'] for body in messages_body}
    ncbi_query = {body['request_info']['ncbi_query'] for body in messages_body}
    study_ids = [body['study_id'] for body in messages_body]
    study_ids.sort()

    assert 1 == len(request_id)
    assert expected_request_id in request_id
    assert 1 == len(ncbi_query)
    assert _S_QUERY['query'] in ncbi_query
    assert [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391] == study_ids


def test_d_get_study_gse(lambda_client, sqs_client, database_holder):
    function_name = 'D_get_study_gse'

    expected_request_id = _provide_random_request_id()
    expected_study_id = 200126815
    expected_gse = str(expected_study_id).replace('200', 'GSE', 3)

    expected_body = json.dumps({'request_info': {'request_id': expected_request_id, 'ncbi_query': _S_QUERY['query']}, 'study_id': expected_study_id}).replace('"', '\"')

    _store_test_request(database_holder, expected_request_id, _S_QUERY['query'])

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_body)))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder
    database_cursor.execute(f"select id, ncbi_id, request_id, gse from sracollector_dev.geo_study where request_id='{expected_request_id}'")
    rows = database_cursor.fetchall()

    assert 1 == len(rows)
    assert expected_study_id == rows[0][1]
    assert expected_gse == rows[0][3]

    messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=1)

    messages_body = [json.loads(message['Body']) for message in messages]

    request_id = {body['request_id'] for body in messages_body}
    ncbi_query = {body['ncbi_query'] for body in messages_body}
    study_id = {body['study_id'] for body in messages_body}
    gse = {body['gse'] for body in messages_body}

    assert 1 == len(request_id)
    assert expected_request_id in request_id
    assert 1 == len(ncbi_query)
    assert _S_QUERY['query'] in ncbi_query
    assert 1 == len(study_id)
    assert f'{expected_study_id}' in study_id
    assert 1 == len(gse)
    assert expected_gse in gse


def test_e_get_study_srp(lambda_client, sqs_client, database_holder):
    function_name = 'E_get_study_srp'

    expected_request_id = _provide_random_request_id()
    expected_study_id = 200126815
    expected_gse = str(expected_study_id).replace('200', 'GSE', 3)
    expected_srp = 'SRP185522'

    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': _S_QUERY['query'], 'study_id': expected_study_id, 'gse': expected_gse}).replace('"', '\"')

    _store_test_request(database_holder, expected_request_id, _S_QUERY['query'])
    inserted_geo_study_id = _store_test_study(database_holder, expected_study_id, expected_request_id, expected_gse)

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_body)))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder
    database_cursor.execute(f"select srp from sracollector_dev.sra_project where geo_study_id='{inserted_geo_study_id}'")
    rows = database_cursor.fetchall()

    assert 1 == len(rows)
    assert expected_srp == rows[0][0]

    messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=1)

    messages_body = [json.loads(message['Body']) for message in messages]

    request_id = {body['request_id'] for body in messages_body}
    ncbi_query = {body['ncbi_query'] for body in messages_body}
    study_id = {body['study_id'] for body in messages_body}
    gse = {body['gse'] for body in messages_body}
    srp = {body['srp'] for body in messages_body}

    assert 1 == len(request_id)
    assert expected_request_id in request_id
    assert 1 == len(ncbi_query)
    assert _S_QUERY['query'] in ncbi_query
    assert 1 == len(study_id)
    assert expected_study_id in study_id
    assert 1 == len(gse)
    assert expected_gse in gse
    assert 1 == len(srp)
    assert expected_srp in srp


def test_e_get_study_srp_attribute_error(lambda_client, sqs_client, database_holder):
    function_name = 'E_get_study_srp'

    expected_request_id = _provide_random_request_id()
    expected_ncbi_query = 'RNA-Seq analysis of genes and pathways involved in the TGF-β-driven transformation of fibroblasts to myofibroblasts'
    expected_study_id = 200110021
    expected_gse = str(expected_study_id).replace('200', 'GSE', 3)
    expected_pysradb_error = 'ATTRIBUTE_ERROR'

    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': expected_ncbi_query, 'study_id': expected_study_id, 'gse': expected_gse}).replace('"', '\"')

    _store_test_request(database_holder, expected_request_id, expected_ncbi_query)
    inserted_geo_study_id = _store_test_study(database_holder, expected_study_id, expected_request_id, expected_gse)

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_body)))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder
    database_cursor.execute(f'select srp from sracollector_dev.sra_project where geo_study_id={inserted_geo_study_id}')
    ok_rows = database_cursor.fetchall()

    assert 0 == len(ok_rows)

    database_cursor.execute(f"select * from sracollector_dev.sra_project_missing where geo_study_id='{inserted_geo_study_id}'")
    ko_rows = database_cursor.fetchall()

    database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where name='{expected_pysradb_error}'")
    pysradb_error_reference_id = database_cursor.fetchone()[0]

    assert 1 == len(ko_rows)
    assert pysradb_error_reference_id == ko_rows[0][2]
    assert "'NoneType' object has no attribute 'rename'" == ko_rows[0][3]


## TODO test de keyerror
## TODO test de muchos mensajes recibidos al mismo tiempo, en todas

def test_e_get_study_srp_value_error(lambda_client, sqs_client, database_holder):
    function_name = 'E_get_study_srp'

    expected_request_id = _provide_random_request_id()
    expected_ncbi_query = 'Topology of the human and mouse m6A RNA methylomes revealed by m6A-seq'
    expected_study_id = 20037005
    expected_gse = str(expected_study_id).replace('200', 'GSE', 3)
    expected_pysradb_error = 'VALUE_ERROR'

    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': expected_ncbi_query, 'study_id': expected_study_id, 'gse': expected_gse}).replace('"', '\"')

    _store_test_request(database_holder, expected_request_id, expected_ncbi_query)
    inserted_geo_study_id = _store_test_study(database_holder, expected_study_id, expected_request_id, expected_gse)

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_body)))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder
    database_cursor.execute(f'select srp from sracollector_dev.sra_project where geo_study_id={inserted_geo_study_id}')
    ok_rows = database_cursor.fetchall()

    assert 0 == len(ok_rows)

    database_cursor.execute(f"select * from sracollector_dev.sra_project_missing where geo_study_id='{inserted_geo_study_id}'")
    ko_rows = database_cursor.fetchall()

    database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where name='{expected_pysradb_error}'")
    pysradb_error_reference_id = database_cursor.fetchone()[0]

    assert 1 == len(ko_rows)
    assert pysradb_error_reference_id == ko_rows[0][2]
    assert 'All arrays must be of the same length' == ko_rows[0][3]


def test_e_get_study_srp_key_error(lambda_client, sqs_client, database_holder):
    function_name = 'E_get_study_srp'

    expected_request_id = _provide_random_request_id()
    expected_ncbi_query = 'Astrocyte-produced HB-EGF limits autoimmune CNS pathology RNA-Seq'
    expected_study_id = 200225606
    expected_gse = str(expected_study_id).replace('200', 'GSE', 3)
    expected_pysradb_error = 'KEY_ERROR'

    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': expected_ncbi_query, 'study_id': expected_study_id, 'gse': expected_gse}).replace('"', '\"')

    _store_test_request(database_holder, expected_request_id, expected_ncbi_query)
    inserted_geo_study_id = _store_test_study(database_holder, expected_study_id, expected_request_id, expected_gse)

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_body)))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder
    database_cursor.execute(f'select srp from sracollector_dev.sra_project where geo_study_id={inserted_geo_study_id}')
    ok_rows = database_cursor.fetchall()

    assert 0 == len(ok_rows)

    database_cursor.execute(f"select * from sracollector_dev.sra_project_missing where geo_study_id='{inserted_geo_study_id}'")
    ko_rows = database_cursor.fetchall()

    database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where name='{expected_pysradb_error}'")
    pysradb_error_reference_id = database_cursor.fetchone()[0]

    assert 1 == len(ko_rows)
    assert pysradb_error_reference_id == ko_rows[0][2]
    assert "'Summary'" == ko_rows[0][3]


def test_f_get_study_srrs(lambda_client, sqs_client, database_holder):
    function_name = 'F_get_study_srrs'

    expected_request_id = _provide_random_request_id()
    expected_study_id = 200221624
    expected_gse = str(expected_study_id).replace('200', 'GSE', 3)
    expected_srp = 'SRP414713'
    expected_srrs = ['SRR22873806', 'SRR22873807', 'SRR22873808', 'SRR22873809', 'SRR22873810', 'SRR22873811', 'SRR22873812', 'SRR22873813', 'SRR22873814']

    expected_body = (json.dumps({'request_id': expected_request_id, 'ncbi_query': _S_QUERY['query'], 'study_id': expected_study_id, 'gse': expected_gse, 'srp': expected_srp})
                     .replace('"', '\"'))

    _store_test_request(database_holder, expected_request_id, _S_QUERY['query'])
    inserted_geo_study_id = _store_test_study(database_holder, expected_study_id, expected_request_id, expected_gse)
    inserted_sra_project_id = _store_test_srp(database_holder, expected_srp, inserted_geo_study_id)

    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(function_name, expected_body)))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder
    database_cursor.execute(f"select srr from sracollector_dev.sra_run where sra_project_id='{inserted_sra_project_id}'")
    rows = database_cursor.fetchall()

    assert len(expected_srrs) == len(rows)
    srrs_in_database = [row[0] for row in rows]
    srrs_in_database.sort()
    assert expected_srrs == srrs_in_database

    messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_srrs))

    messages_body = [json.loads(message['Body']) for message in messages]

    request_id = {body['request_id'] for body in messages_body}
    ncbi_query = {body['ncbi_query'] for body in messages_body}
    study_id = {body['study_id'] for body in messages_body}
    gse = {body['gse'] for body in messages_body}
    srp = {body['srp'] for body in messages_body}
    srrs = [body['srr'] for body in messages_body]
    srrs.sort()

    assert 1 == len(request_id)
    assert expected_request_id in request_id
    assert 1 == len(ncbi_query)
    assert _S_QUERY['query'] in ncbi_query
    assert 1 == len(study_id)
    assert expected_study_id in study_id
    assert 1 == len(gse)
    assert expected_gse in gse
    assert 1 == len(srp)
    assert expected_srp in srp
    assert len(expected_srrs) == len(srrs)
    assert expected_srrs == srrs
