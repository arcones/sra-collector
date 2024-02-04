import json
import random
import string
import time

import boto3
import botocore
import psycopg2
import pytest
import urllib3

SQS_TEST_QUEUE = 'https://sqs.eu-central-1.amazonaws.com/120715685161/integration_test_queue'

http = urllib3.PoolManager()

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits
expected_request_id = ''.join(random.choice(CHARACTERS) for char in range(20))
expected_ncbi_query = ''.join(random.choice(CHARACTERS) for another_char in range(50))


@pytest.fixture(scope='session', autouse=True)
def init_tests():
    _wait_test_server_readiness()


@pytest.fixture(scope='session', autouse=True)
def database_cursor():
    database_connection = _get_db_connection()
    cursor = database_connection.cursor()
    cursor.execute('TRUNCATE TABLE sracollector_dev.REQUEST CASCADE;')
    database_connection.commit()
    yield cursor
    cursor.close()
    database_connection.close()


@pytest.fixture(scope='session', autouse=True)
def sqs_client():
    sqs_client = boto3.client('sqs', region_name='eu-central-1')
    try:
        sqs_client.purge_queue(QueueUrl=SQS_TEST_QUEUE)
    except sqs_client.exceptions.PurgeQueueInProgress as purgeQueueActionInProgress:
        print(f'There is a purge action already in progress for test SQS')
    _ensure_queue_is_empty(sqs_client)
    yield sqs_client
    sqs_client.close()


@pytest.fixture(scope='session', autouse=True)
def lambda_client():
    botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=90, retries={'max_attempts': 0})
    lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)
    yield lambda_client
    lambda_client.close()


def test_a_get_user_query(sqs_client, lambda_client):
    lambda_function = 'A_get_user_query'
    expected_body = json.dumps({'ncbi_query': expected_ncbi_query}).replace('"', '\"')

    _print_test_params(lambda_function, expected_body)

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['requestContext']['requestId'] = expected_request_id
        payload['body'] = expected_body
        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    actual_response = json.loads(response['Payload'].read())

    actual_response_inner_status = actual_response['statusCode']
    actual_response_payload = actual_response['body']

    assert 201 == actual_response_inner_status
    assert f'{{"request_id": "{expected_request_id}", "ncbi_query": "{expected_ncbi_query}"}}' == actual_response_payload
    assert 200 == response['StatusCode']

    sqs_messages = sqs_client.receive_message(QueueUrl=SQS_TEST_QUEUE)

    if 'Messages' in sqs_messages:
        sqs_message = sqs_messages['Messages'][0]
        sqs_message_payload = json.loads(sqs_message['Body'])

        assert expected_request_id == sqs_message_payload['request_id']
        assert expected_ncbi_query == sqs_message_payload['ncbi_query']

        sqs_client.delete_message(QueueUrl=SQS_TEST_QUEUE, ReceiptHandle=sqs_message['ReceiptHandle'])
    else:
        pytest.xfail(f'Expected at least one message in the queue but got {sqs_messages}')


def test_b_paginate_user_query_just_one_page(database_cursor, sqs_client, lambda_client):
    lambda_function = 'B_paginate_user_query'
    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': expected_ncbi_query}).replace('"', '\"')

    _print_test_params(lambda_function, expected_body)

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['Records'][0]['body'] = expected_body

        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    database_cursor.execute(f"select id, query from sracollector_dev.request where id='{expected_request_id}'")
    rows = database_cursor.fetchall()

    assert 1 == len(rows)
    assert expected_request_id == rows[0][0]
    assert expected_ncbi_query == rows[0][1]
    assert 200 == response['StatusCode']

    sqs_messages = sqs_client.receive_message(QueueUrl=SQS_TEST_QUEUE)

    if 'Messages' in sqs_messages:
        sqs_message = sqs_messages['Messages'][0]
        sqs_message_payload = json.loads(sqs_message['Body'])

        assert expected_request_id == sqs_message_payload['request_id']
        assert expected_ncbi_query == sqs_message_payload['ncbi_query']
        assert 0 == sqs_message_payload['retstart']
        assert 500 == sqs_message_payload['retmax']

        sqs_client.delete_message(QueueUrl=SQS_TEST_QUEUE, ReceiptHandle=sqs_message['ReceiptHandle'])
    else:
        print(f'Expected at least one message in the queue but got {sqs_messages}')
        pytest.xfail()


def _print_test_params(lambda_function: str, params: str) -> None:
    print(f'\nIn {lambda_function} test were used: {params}')


def test_b_paginate_user_query_several_pages(database_cursor, sqs_client, lambda_client):
    lambda_function = 'B_paginate_user_query'
    expected_controlled_ncbi_query = 'rna seq and homo sapiens and myeloid and leukemia'
    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': expected_controlled_ncbi_query}).replace('"', '\"')

    _print_test_params(lambda_function, expected_body)

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['Records'][0]['body'] = expected_body

        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    database_cursor.execute(f"select id, query, geo_count from sracollector_dev.request where id='{expected_request_id}'")
    rows = database_cursor.fetchall()

    assert 1 == len(rows)
    assert expected_request_id == rows[0][0]
    assert expected_controlled_ncbi_query == rows[0][1]
    assert 1088 <= rows[0][2]
    assert 200 == response['StatusCode']

    messages = _get_all_queue_messages(sqs_client)

    messages_body = [json.loads(message['Body']) for message in messages]

    request_id = {body['request_id'] for body in messages_body}
    ncbi_query = {body['ncbi_query'] for body in messages_body}
    retmax = {body['retmax'] for body in messages_body}
    retstarts = [body['retstart'] for body in messages_body]
    retstarts.sort()

    assert 1 == len(request_id)
    assert expected_request_id in request_id
    assert 1 == len(ncbi_query)
    assert expected_controlled_ncbi_query in ncbi_query
    assert 1 == len(retmax)
    assert 500 in retmax
    assert 3 == len(retstarts)
    assert [0, 500, 1000] == retstarts


def _get_db_connection():
    secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
    database_credentials = secrets_client.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
    secrets_client.close()
    username = json.loads(database_credentials['SecretString'])['username']
    password = json.loads(database_credentials['SecretString'])['password']
    host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'

    connection_string = f"host={host} dbname='sracollector' user='{username}' password='{password}'"
    print('DB connection ready :)')
    return psycopg2.connect(connection_string)


def _wait_test_server_readiness():
    is_test_still_initializing = True
    start_waiting = time.time()
    while is_test_still_initializing:
        try:
            response = http.urlopen('GET', 'http://localhost:3001')
            if response.status == 404:
                print('Test server is ready :)')
                is_test_still_initializing = False
        except Exception as connection_refused_error:
            if time.time() - start_waiting < 60:
                print('Tests are still initializing...')
                time.sleep(5)
            else:
                print('Timeout while waiting test server to launch :(')
                raise connection_refused_error


def _ensure_queue_is_empty(sqs_client):
    messages_left = None
    start_waiting = time.time()
    while messages_left != 0:
        response = sqs_client.get_queue_attributes(QueueUrl=SQS_TEST_QUEUE, AttributeNames=['ApproximateNumberOfMessages'])
        messages_left = int(response['Attributes']['ApproximateNumberOfMessages'])
        if time.time() - start_waiting < 60:
            print('SQS queue is still not empty...')
            time.sleep(5)
        else:
            print('Timeout while waiting SQS queue to be purged :(')
            raise Exception
    print('SQS queue is purged :)')


def _get_all_queue_messages(sqs_client):
    messages = []

    while len(messages) < 3:
        sqs_messages = sqs_client.receive_message(QueueUrl=SQS_TEST_QUEUE)
        if 'Messages' in sqs_messages:
            for message in sqs_messages['Messages']:
                if message not in messages:
                    messages.append(message)
                    sqs_client.delete_message(QueueUrl=SQS_TEST_QUEUE, ReceiptHandle=message['ReceiptHandle'])
        else:
            time.sleep(0.1)
            continue

    return messages
