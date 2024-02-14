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
_2XL_QUERY = {'query': 'rna seq and homo sapiens and myeloid and leukemia', 'results': 1091}


@pytest.fixture(scope='session', autouse=True)
def init_tests():
    _wait_test_server_readiness()


@pytest.fixture(scope='session', autouse=True)
def lambda_client():
    botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=360, retries={'max_attempts': 0})
    lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)
    yield lambda_client
    lambda_client.close()


@pytest.fixture(scope='session', autouse=True)
def sqs_client():
    sqs_client = boto3.client('sqs', region_name='eu-central-1')
    try:
        sqs_client.purge_queue(QueueUrl=SQS_TEST_QUEUE)
    except sqs_client.exceptions.PurgeQueueInProgress:
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
        TRUNCATE TABLE sracollector_dev.sra_run_missing cascade;
        TRUNCATE TABLE sracollector_dev.sra_project_missing cascade;
        TRUNCATE TABLE sracollector_dev.sra_project cascade;
        TRUNCATE TABLE sracollector_dev.geo_study cascade;
        TRUNCATE TABLE sracollector_dev.geo_experiment cascade;
        TRUNCATE TABLE sracollector_dev.request cascade;
    """)
    database_connection.commit()
    yield database_cursor, database_connection
    database_cursor.close()
    database_connection.close()


def test_a_get_user_query(lambda_client, sqs_client):
    # GIVEN
    function_name = 'A_get_user_query'

    request_id = _provide_random_request_id()
    ncbi_query = _provide_random_ncbi_query()
    input_body = json.dumps({'ncbi_query': ncbi_query}).replace('"', '\"')

    with open(f'tests/fixtures/{function_name}_input.json') as json_data:
        payload = json.load(json_data)
        payload['requestContext']['requestId'] = request_id
        payload['body'] = input_body

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(payload))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    actual_response = json.loads(response['Payload'].read())

    actual_response_inner_status = actual_response['statusCode']
    actual_response_payload = actual_response['body']

    assert actual_response_inner_status == 201
    assert actual_response_payload == f'{{"request_id": "{request_id}", "ncbi_query": "{ncbi_query}"}}'

    # THEN REGARDING MESSAGES
    messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=1)

    sqs_message = messages[0]
    sqs_message_payload = json.loads(sqs_message['Body'])

    assert sqs_message_payload['request_id'] == request_id
    assert sqs_message_payload['ncbi_query'] == ncbi_query


def test_b_get_query_pages(lambda_client, sqs_client, database_holder):
    # GIVEN
    function_name = 'B_get_query_pages'

    request_id_1 = _provide_random_request_id()
    request_id_2 = _provide_random_request_id()
    input_bodies = [
        json.dumps({'request_id': request_id_1, 'ncbi_query': _S_QUERY['query']}).replace('"', '\"'),
        json.dumps({'request_id': request_id_2, 'ncbi_query': _2XL_QUERY['query']}).replace('"', '\"'),
    ]

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING DATA
    database_cursor, _ = database_holder

    database_cursor.execute(f"select id, query, geo_count from sracollector_dev.request where id in ('{request_id_1}', '{request_id_2}')")
    actual_rows = database_cursor.fetchall()
    actual_rows = sorted(actual_rows, key=lambda row: (row[0]))

    expected_rows = [
        (request_id_1, _S_QUERY['query'], _S_QUERY['results']),
        (request_id_2, _2XL_QUERY['query'], _2XL_QUERY['results'])
    ]
    expected_rows = sorted(expected_rows, key=lambda row: (row[0]))

    assert actual_rows == expected_rows

    # THEN REGARDING MESSAGES
    expected_message_bodies = [{'request_id': request_id_1, 'ncbi_query': _S_QUERY['query'], 'retstart': 0, 'retmax': 500},
                               {'request_id': request_id_2, 'ncbi_query': _2XL_QUERY['query'], 'retstart': 0, 'retmax': 500},
                               {'request_id': request_id_2, 'ncbi_query': _2XL_QUERY['query'], 'retstart': 500, 'retmax': 500},
                               {'request_id': request_id_2, 'ncbi_query': _2XL_QUERY['query'], 'retstart': 1000, 'retmax': 500}]
    expected_message_bodies = sorted(expected_message_bodies, key=lambda message: (message['request_id'], message['retstart']))

    actual_messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_message_bodies))
    actual_message_bodies = [json.loads(message['Body']) for message in actual_messages]
    actual_message_bodies = sorted(actual_message_bodies, key=lambda message: (message['request_id'], message['retstart']))

    assert actual_message_bodies == expected_message_bodies


def test_c_get_study_ids(lambda_client, sqs_client):
    # GIVEN
    function_name = 'C_get_study_ids'

    request_id_1 = _provide_random_request_id()
    request_id_2 = _provide_random_request_id()
    input_bodies = [
        json.dumps({'request_id': request_id_1, 'ncbi_query': _S_QUERY['query'], 'retstart': 0, 'retmax': 500}).replace('"', '\"'),
        json.dumps({'request_id': request_id_2, 'ncbi_query': _S_QUERY['query'], 'retstart': 0, 'retmax': 500}).replace('"', '\"'),
    ]

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING MESSAGES
    expected_study_ids = [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391]

    expected_message_bodies = \
        [{'ncbi_query': _S_QUERY['query'], 'request_id': request_id_1, 'study_id': expected_study_id} for expected_study_id in expected_study_ids] + \
        [{'ncbi_query': _S_QUERY['query'], 'request_id': request_id_2, 'study_id': expected_study_id} for expected_study_id in expected_study_ids]
    expected_message_bodies = sorted(expected_message_bodies, key=lambda message: (message['request_id'], message['study_id']))

    actual_messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_message_bodies))
    actual_message_bodies = [json.loads(message['Body']) for message in actual_messages]
    actual_message_bodies = sorted(actual_message_bodies, key=lambda message: (message['request_id'], message['study_id']))

    assert actual_message_bodies == expected_message_bodies


def test_d_get_study_geo_gse(lambda_client, sqs_client, database_holder):
    # GIVEN
    function_name = 'D_get_study_geo'

    request_id = _provide_random_request_id()
    study_ids = [200126815, 200150644, 200167593]
    gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
    study_ids_and_gse = list(zip(study_ids, gses))

    input_bodies = [
        json.dumps({'request_id': request_id, 'ncbi_query': _S_QUERY['query'], 'study_id': study_id}).replace('"', '\"')
        for study_id in study_ids
    ]

    _store_test_request(database_holder, request_id, _S_QUERY['query'])

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING DATA
    database_cursor, _ = database_holder
    database_cursor.execute(f"select ncbi_id, request_id, gse from sracollector_dev.geo_study where request_id='{request_id}'")
    actual_rows = database_cursor.fetchall()
    actual_rows = sorted(actual_rows, key=lambda row: (row[0]))

    expected_rows = [(study_id_and_gse[0], request_id, study_id_and_gse[1]) for study_id_and_gse in study_ids_and_gse]
    expected_rows = sorted(expected_rows, key=lambda row: (row[0]))

    assert actual_rows == expected_rows

    database_cursor.execute(f"select ncbi_id, request_id from sracollector_dev.geo_experiment where request_id='{request_id}'")
    actual_rows = database_cursor.fetchall()
    assert actual_rows == []

    # THEN REGARDING MESSAGES
    expected_message_bodies = [
        {'request_id': request_id, 'study_id': study_id_and_gse[0], 'gse': study_id_and_gse[1]}
        for study_id_and_gse in study_ids_and_gse
    ]
    expected_message_bodies = sorted(expected_message_bodies, key=lambda message: (message['study_id']))

    actual_messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_message_bodies))
    actual_message_bodies = [json.loads(message['Body']) for message in actual_messages]
    actual_message_bodies = sorted(actual_message_bodies, key=lambda message: (message['study_id']))

    assert actual_message_bodies == expected_message_bodies


def test_d_get_study_geo_gsm(lambda_client, sqs_client, database_holder):
    # GIVEN
    function_name = 'D_get_study_geo'

    request_id = _provide_random_request_id()
    study_ids = [305668979, 305668862, 305668694]
    gsms = [str(study_id).replace('30', 'GSM', 3) for study_id in study_ids]
    study_ids_and_gsms = list(zip(study_ids, gsms))

    input_bodies = [
        json.dumps({'request_id': request_id, 'ncbi_query': _S_QUERY['query'], 'study_id': study_id}).replace('"', '\"')
        for study_id in study_ids
    ]

    _store_test_request(database_holder, request_id, _S_QUERY['query'])

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING DATA
    database_cursor, _ = database_holder
    database_cursor.execute(f"select ncbi_id, request_id, gsm from sracollector_dev.geo_experiment where request_id='{request_id}'")
    actual_rows = database_cursor.fetchall()
    actual_rows = sorted(actual_rows, key=lambda row: (row[0]))

    expected_rows = [(study_id_and_gsm[0], request_id, study_id_and_gsm[1]) for study_id_and_gsm in study_ids_and_gsms]
    expected_rows = sorted(expected_rows, key=lambda row: (row[0]))

    assert actual_rows == expected_rows

    database_cursor.execute(f"select ncbi_id, request_id, gse from sracollector_dev.geo_study where request_id='{request_id}'")
    actual_rows = database_cursor.fetchall()
    assert actual_rows == []

    # THEN REGARDING MESSAGES
    actual_messages = int(sqs_client.get_queue_attributes(QueueUrl=SQS_TEST_QUEUE, AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages'])

    assert actual_messages == 0


def test_e_get_study_srp_ok(lambda_client, sqs_client, database_holder):
    # GIVEN
    function_name = 'E_get_study_srp'

    request_id = _provide_random_request_id()
    study_ids = [200126815, 200150644, 200167593]
    gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]

    srps = ['SRP185522', 'SRP261818', 'SRP308347']

    study_ids_and_gses = list(zip(study_ids, gses))

    input_bodies = [
        json.dumps({'request_id': request_id, 'ncbi_query': _S_QUERY['query'], 'study_id': study_id_and_gse[0], 'gse': study_id_and_gse[1]})
        .replace('"', '\"')
        for study_id_and_gse in study_ids_and_gses
    ]

    _store_test_request(database_holder, request_id, _S_QUERY['query'])

    inserted_geo_study_ids = []
    for study_id_and_gse in study_ids_and_gses:
        inserted_geo_study_ids.append(_store_test_study(database_holder, request_id, study_id_and_gse[0], study_id_and_gse[1]))

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING DATA
    database_cursor, _ = database_holder
    inserted_geo_study_ids_for_sql_in = ','.join(map(str, inserted_geo_study_ids))

    database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                where geo_study_id in ({inserted_geo_study_ids_for_sql_in})
                            ''')
    actual_ok_rows = database_cursor.fetchall()
    expected_ok_rows = [(expected_srp,) for expected_srp in srps]
    assert actual_ok_rows == expected_ok_rows

    database_cursor.execute(f'select * from sracollector_dev.sra_project_missing where geo_study_id in ({inserted_geo_study_ids_for_sql_in})')
    actual_ko_rows = database_cursor.fetchall()
    assert actual_ko_rows == []

    # THEN REGARDING MESSAGES
    study_ids_and_gses_and_srps = list(zip(study_ids_and_gses, srps))

    expected_message_bodies = [
        {
            'request_id': request_id,
            'ncbi_query': _S_QUERY['query'],
            'study_id': study_id_and_gse_and_srp[0][0],
            'gse': study_id_and_gse_and_srp[0][1],
            'srp': study_id_and_gse_and_srp[1]
        }
        for study_id_and_gse_and_srp in study_ids_and_gses_and_srps
    ]
    expected_message_bodies = sorted(expected_message_bodies, key=lambda message: (message['study_id']))

    actual_messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_message_bodies))
    actual_message_bodies = [json.loads(message['Body']) for message in actual_messages]
    actual_message_bodies = sorted(actual_message_bodies, key=lambda message: (message['study_id']))

    assert actual_message_bodies == expected_message_bodies


def test_e_get_study_srp_ko(lambda_client, sqs_client, database_holder):
    # GIVEN
    function_name = 'E_get_study_srp'

    request_id = _provide_random_request_id()

    study_ids = [200110021, 20037005, 200225606]
    gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]

    study_ids_and_gses = list(zip(study_ids, gses))

    input_bodies = [
        json.dumps({'request_id': request_id, 'ncbi_query': _S_QUERY['query'], 'study_id': study_id_and_gse[0], 'gse': study_id_and_gse[1]})
        .replace('"', '\"')
        for study_id_and_gse in study_ids_and_gses
    ]

    _store_test_request(database_holder, request_id, _S_QUERY['query'])

    inserted_geo_study_ids = []
    for study_id_and_gse in study_ids_and_gses:
        inserted_geo_study_ids.append(_store_test_study(database_holder, request_id, study_id_and_gse[0], study_id_and_gse[1]))

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING DATA
    database_cursor, _ = database_holder
    inserted_geo_study_ids_for_sql_in = ','.join(map(str, inserted_geo_study_ids))

    database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                where geo_study_id in ({inserted_geo_study_ids_for_sql_in})
                            ''')
    actual_ok_rows = database_cursor.fetchall()
    assert actual_ok_rows == []

    pysradb_errors_for_sql_in = ','.join(["'ATTRIBUTE_ERROR'", "'VALUE_ERROR'", "'KEY_ERROR'"])
    database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='gse_to_srp' and name in ({pysradb_errors_for_sql_in})")
    pysradb_error_reference_ids = [pysradb_error_reference_row[0] for pysradb_error_reference_row in database_cursor.fetchall()]
    expected_details = ["'NoneType' object has no attribute 'rename'", 'All arrays must be of the same length', "'Summary'"]

    database_cursor.execute(f'select pysradb_error_reference_id, details from sracollector_dev.sra_project_missing where geo_study_id in ({inserted_geo_study_ids_for_sql_in})')
    actual_ko_rows = database_cursor.fetchall()
    expected_ko_rows = list(zip(pysradb_error_reference_ids, expected_details))
    assert actual_ko_rows == expected_ko_rows

    # THEN REGARDING MESSAGES
    actual_messages = int(sqs_client.get_queue_attributes(QueueUrl=SQS_TEST_QUEUE, AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages'])

    assert actual_messages == 0


def test_f_get_study_srrs_ok(lambda_client, sqs_client, database_holder):
    function_name = 'F_get_study_srrs'

    request_id = _provide_random_request_id()
    study_ids = [200126815, 200308347]
    gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
    srps = ['SRP414713', 'SRP308347']
    study_ids_and_gses_and_srps = list(zip(study_ids, gses, srps))
    srrs_for_srp414713 = ['SRR22873806', 'SRR22873807', 'SRR22873808', 'SRR22873809', 'SRR22873810', 'SRR22873811', 'SRR22873812', 'SRR22873813', 'SRR22873814']
    srrs_for_srp308347 = ['SRR13790583', 'SRR13790584', 'SRR13790585', 'SRR13790586', 'SRR13790587', 'SRR13790588', 'SRR13790589', 'SRR13790590', 'SRR13790591', 'SRR13790592',
                          'SRR13790593', 'SRR13790594']

    input_bodies = [
        json.dumps({
            'request_id': request_id,
            'ncbi_query': _S_QUERY['query'],
            'study_id': study_id_and_gse_and_srp[0],
            'gse': study_id_and_gse_and_srp[1],
            'srp': study_id_and_gse_and_srp[2]
        }).replace('"', '\"')
        for study_id_and_gse_and_srp in study_ids_and_gses_and_srps
    ]

    _store_test_request(database_holder, request_id, _S_QUERY['query'])
    inserted_geo_study_ids = []
    for study_id_and_gse_and_srp in study_ids_and_gses_and_srps:
        inserted_geo_study_ids.append(_store_test_study(database_holder, request_id, study_id_and_gse_and_srp[0], study_id_and_gse_and_srp[1]))

    inserted_sra_project_ids = []
    for index, study_id_and_gse_and_srp in enumerate(study_ids_and_gses_and_srps):
        # TODO AQUI ME QUEDE, ADAPTAR LOS TESTS DE F (Y EL CODIGO) A LA NUEVFA TABLA M:N Y A ESA ESTRUCTURA DE DATOS
        inserted_sra_project_ids.append(_store_test_srp(database_holder, study_id_and_gse_and_srp[2], inserted_geo_study_ids[index]))

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING DATA
    database_cursor, _ = database_holder
    inserted_sra_project_id_for_sql_in = ','.join(map(str, inserted_sra_project_ids))
    database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
    actual_ok_rows = database_cursor.fetchall()
    actual_ok_rows = actual_ok_rows.sort()
    expected_rows = [(srr,) for srr in (srrs_for_srp414713, srrs_for_srp308347)]
    expected_rows = expected_rows.sort()
    assert actual_ok_rows == expected_rows

    database_cursor.execute(f'select * from sracollector_dev.sra_run_missing where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
    actual_ko_rows = database_cursor.fetchall()
    assert actual_ko_rows == []

    # THEN REGARDING MESSAGES
    expected_message_bodies_srp308347 = [
        {
            'request_id': request_id,
            'ncbi_query': _S_QUERY['query'],
            'study_id': 200308347,
            'gse': 'GSE308347',
            'srp': 'SRP308347',
            'srr': srr,
        }
        for srr in srrs_for_srp308347
    ]
    expected_message_bodies_srp414713 = [
        {
            'request_id': request_id,
            'ncbi_query': _S_QUERY['query'],
            'study_id': 200126815,
            'gse': 'GSE126815',
            'srp': 'SRP414713',
            'srr': srr,
        }
        for srr in srrs_for_srp414713
    ]

    expected_message_bodies = sorted((expected_message_bodies_srp308347 + expected_message_bodies_srp414713),
                                     key=lambda message: (message['request_id'], message['study_id'], message['srr']))

    actual_messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_message_bodies))
    actual_message_bodies = [json.loads(message['Body']) for message in actual_messages]
    actual_message_bodies = sorted(actual_message_bodies, key=lambda message: (message['request_id'], message['study_id'], message['srr']))

    assert len(actual_message_bodies) == len(expected_message_bodies)
    assert actual_message_bodies == expected_message_bodies


def test_f_get_study_srrs_ko(lambda_client, sqs_client, database_holder):
    function_name = 'F_get_study_srrs'

    request_id = _provide_random_request_id()
    study_ids = [200126815, 200118257]
    gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
    srps = ['SRP185522', 'SRP178139']
    study_ids_and_gses_and_srps = list(zip(study_ids, gses, srps))

    input_bodies = [
        json.dumps({
            'request_id': request_id,
            'ncbi_query': _S_QUERY['query'],
            'study_id': study_id_and_gse_and_srp[0],
            'gse': study_id_and_gse_and_srp[1],
            'srp': study_id_and_gse_and_srp[2]
        }).replace('"', '\"')
        for study_id_and_gse_and_srp in study_ids_and_gses_and_srps
    ]

    _store_test_request(database_holder, request_id, _S_QUERY['query'])
    inserted_geo_study_ids = []
    for study_id_and_gse_and_srp in study_ids_and_gses_and_srps:
        inserted_geo_study_ids.append(_store_test_study(database_holder, request_id, study_id_and_gse_and_srp[0], study_id_and_gse_and_srp[1]))

    inserted_sra_project_ids = []
    for index, study_id_and_gse_and_srp in enumerate(study_ids_and_gses_and_srps):
        inserted_sra_project_ids.append(_store_test_srp(database_holder, study_id_and_gse_and_srp[2], inserted_geo_study_ids[index]))

    # WHEN
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name)))

    # THEN REGARDING LAMBDA
    assert response['StatusCode'] == 200

    # THEN REGARDING DATA
    database_cursor, _ = database_holder
    inserted_sra_project_id_for_sql_in = ','.join(map(str, inserted_sra_project_ids))
    database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
    actual_ok_rows = database_cursor.fetchall()
    assert actual_ok_rows == []

    database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='srp_to_srr' and name='ATTRIBUTE_ERROR'")
    pysradb_error_reference_id = database_cursor.fetchone()[0]
    expected_detail = "'NoneType' object has no attribute 'columns'"

    database_cursor.execute(f'select pysradb_error_reference_id, details from sracollector_dev.sra_run_missing where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
    actual_ko_rows = database_cursor.fetchall()
    assert actual_ko_rows == [(pysradb_error_reference_id, expected_detail), (pysradb_error_reference_id, expected_detail)]

    # THEN REGARDING MESSAGES
    actual_messages = int(sqs_client.get_queue_attributes(QueueUrl=SQS_TEST_QUEUE, AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages'])

    assert actual_messages == 0

#
# def test_f_get_study_srrs_expensive_srp(lambda_client, sqs_client, database_holder):
#     function_name = 'F_get_study_srrs'
#
#     request_id = _provide_random_request_id()
#     study_ids = [200177646, 200177191, 200176705, 200208520, 200177936, 200177125, 200176891, 200177518, 200176867, 200215537]
#
#     gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
#     srp = 'SRP012412'
#     srps = [srp] * 10
#     study_ids_and_gses_and_srps = list(zip(study_ids, gses, srps))
#
#     with open(f'tests/fixtures/SRRS_of_SRP012412.txt') as file_with_expected_srrs:
#         srrs = file_with_expected_srrs.readlines()
#
#     input_bodies = [
#         json.dumps({
#             'request_id': request_id,
#             'ncbi_query': _S_QUERY['query'],
#             'study_id': study_id_and_gse_and_srp[0],
#             'gse': study_id_and_gse_and_srp[1],
#             'srp': study_id_and_gse_and_srp[2]
#         }).replace('"', '\"')
#         for study_id_and_gse_and_srp in study_ids_and_gses_and_srps
#     ]
#
#     _store_test_request(database_holder, request_id, _S_QUERY['query'])
#     inserted_geo_study_ids = []
#     for study_id_and_gse_and_srp in study_ids_and_gses_and_srps:
#         inserted_geo_study_ids.append(_store_test_study(database_holder, request_id, study_id_and_gse_and_srp[0], study_id_and_gse_and_srp[1]))
#
#     inserted_sra_project_ids = []
#     for index, study_id_and_gse_and_srp in enumerate(study_ids_and_gses_and_srps):
#         inserted_sra_project_ids.append(_store_test_srp(database_holder, study_id_and_gse_and_srp[2], inserted_geo_study_ids[index]))
#
#     # WHEN
#     response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(_get_customized_input_from_sqs(input_bodies, function_name, '_expensive_srp')))
#
#     # THEN REGARDING LAMBDA
#     assert response['StatusCode'] == 200
#
#     # THEN REGARDING DATA
#     database_cursor, _ = database_holder
#     inserted_sra_project_id_for_sql_in = ','.join(map(str, inserted_sra_project_ids))
#     database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
#     actual_ok_rows = database_cursor.fetchall()
#     actual_ok_rows = actual_ok_rows.sort()
#     expected_rows = [(srr,) for srr in (srrs)]
#     expected_rows = expected_rows.sort()
#     assert actual_ok_rows == expected_rows
#
#     database_cursor.execute(f'select * from sracollector_dev.sra_run_missing where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
#     actual_ko_rows = database_cursor.fetchall()
#     assert actual_ko_rows == []
#
#     # THEN REGARDING MESSAGES
#     expected_message_bodies = [
#         {
#             'request_id': request_id,
#             'ncbi_query': _S_QUERY['query'],
#             'study_id': 200308347,
#             'gse': 'GSE308347',
#             'srp': 'SRP308347',
#             'srr': srr,
#         }
#         for srr in srrs
#     ]
#
#     expected_message_bodies = sorted(expected_message_bodies, key=lambda message: (message['request_id'], message['study_id'], message['srr']))
#
#     actual_messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=len(expected_message_bodies))
#     actual_message_bodies = [json.loads(message['Body']) for message in actual_messages]
#     actual_message_bodies = sorted(actual_message_bodies, key=lambda message: (message['request_id'], message['study_id'], message['srr']))
#
#     assert len(actual_message_bodies) == len(expected_message_bodies)
#     assert actual_message_bodies == expected_message_bodies
