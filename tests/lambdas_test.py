import json

import boto3
import botocore
import pytest

from tests.utils_test import _ensure_queue_is_empty
from tests.utils_test import _get_all_queue_messages
from tests.utils_test import _get_db_connection
from tests.utils_test import _print_test_params
from tests.utils_test import _provide_random_ncbi_query
from tests.utils_test import _provide_random_request_id
from tests.utils_test import _wait_test_server_readiness

SQS_TEST_QUEUE = 'https://sqs.eu-central-1.amazonaws.com/120715685161/integration_test_queue'

_2XL_QUERY = 'rna seq and homo sapiens and myeloid and leukemia'
_S_QUERY = 'stroke AND single cell rna seq AND musculus'


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
    database_cursor.execute('TRUNCATE TABLE sracollector_dev.REQUEST CASCADE;')
    database_connection.commit()
    yield database_cursor, database_connection
    database_cursor.close()
    database_connection.close()

def test_a_get_user_query(lambda_client, sqs_client):
    lambda_function = 'A_get_user_query'

    expected_request_id = _provide_random_request_id()
    expected_ncbi_query = _provide_random_ncbi_query()
    expected_body = json.dumps({'ncbi_query': expected_ncbi_query}).replace('"', '\"')

    _print_test_params(lambda_function, expected_body)

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

def test_b_paginate_user_query(lambda_client, sqs_client, database_holder):
    lambda_function = 'B_paginate_user_query'

    expected_request_id = _provide_random_request_id()
    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': _2XL_QUERY}).replace('"', '\"')

    _print_test_params(lambda_function, expected_body)

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['Records'][0]['body'] = expected_body

        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    assert 200 == response['StatusCode']

    database_cursor, _ = database_holder

    database_cursor.execute(f"select id, query, geo_count from sracollector_dev.request where id='{expected_request_id}'")
    rows = database_cursor.fetchall()

    assert 1 == len(rows)
    assert expected_request_id == rows[0][0]
    assert _2XL_QUERY == rows[0][1]
    assert 1088 <= rows[0][2]

    messages = _get_all_queue_messages(sqs_client, SQS_TEST_QUEUE, expected_messages=3)

    messages_body = [json.loads(message['Body']) for message in messages]

    request_id = {body['request_id'] for body in messages_body}
    ncbi_query = {body['ncbi_query'] for body in messages_body}
    retmax = {body['retmax'] for body in messages_body}
    retstarts = [body['retstart'] for body in messages_body]
    retstarts.sort()

    assert 1 == len(request_id)
    assert expected_request_id in request_id
    assert 1 == len(ncbi_query)
    assert _2XL_QUERY in ncbi_query
    assert 1 == len(retmax)
    assert 500 in retmax
    assert 3 == len(retstarts)
    assert [0, 500, 1000] == retstarts

def test_c_get_study_ids(lambda_client, sqs_client):
    lambda_function = 'C_get_study_ids'

    expected_request_id = _provide_random_request_id()
    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': _S_QUERY, 'retstart': 0, 'retmax': 500}).replace('"', '\"')

    _print_test_params(lambda_function, expected_body)

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['Records'][0]['body'] = expected_body

        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

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
    assert _S_QUERY in ncbi_query
    assert [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391] == study_ids


def test_d_get_study_gse(lambda_client, sqs_client, database_holder):
    lambda_function = 'D_get_study_gse'

    expected_request_id = _provide_random_request_id()
    expected_study_id = 200126815
    expected_gse = str(expected_study_id).replace('200', 'GSE', 3)

    expected_body = json.dumps({'request_info': {'request_id': expected_request_id, 'ncbi_query': _S_QUERY}, 'study_id': expected_study_id}).replace('"', '\"')

    database_cursor, database_connection = database_holder

    statement = database_cursor.mogrify(f'insert into sracollector_dev.request (id, query, geo_count) values (%s, %s, %s)', (expected_request_id, _S_QUERY, 1))
    database_cursor.execute(statement)
    database_connection.commit()

    _print_test_params(lambda_function, expected_body)

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['Records'][0]['body'] = expected_body

        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    assert 200 == response['StatusCode']

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
    assert _S_QUERY in ncbi_query
    assert 1 == len(study_id)
    assert f'{expected_study_id}' in study_id
    assert 1 == len(gse)
    assert expected_gse in gse
