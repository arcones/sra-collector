import json
import random
import string
import time

import boto3
import botocore
import psycopg2
import pytest
import urllib3

LAMBDA_TIMEOUT = 90

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits

botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=LAMBDA_TIMEOUT, retries={'max_attempts': 0})

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)

http = urllib3.PoolManager()

expected_request_id = ''.join(random.choice(CHARACTERS) for i in range(20))
expected_ncbi_query = ''.join(random.choice(CHARACTERS) for i in range(50))


@pytest.fixture(scope='session', autouse=True)
def init_tests(request):
    _wait_test_server_readiness()


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


def test_a_get_user_query():
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
    ## TODO probar q el mensaje está en la cola de salida


def test_b_paginate_user_query():
    lambda_function = 'B_paginate_user_query'
    expected_body = json.dumps({'request_id': expected_request_id, 'ncbi_query': expected_ncbi_query}).replace('"', '\"')

    _print_test_params(lambda_function, expected_body)

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['Records'][0]['body'] = expected_body

        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    database_connection = _get_db_connection()
    cursor = database_connection.cursor()
    cursor.execute(f"select id, query from sracollector_dev.request where id='{expected_request_id}'")
    rows = cursor.fetchall()
    cursor.close()
    database_connection.close()

    assert 1 == len(rows)
    assert expected_request_id == rows[0][0]
    assert expected_ncbi_query == rows[0][1]
    assert 200 == response['StatusCode']

    ## TODO probar q el mensaje está en la cola de salida
    ## TODO probar para queries con tronchos paginisticos


def _print_test_params(lambda_function: str, params: str) -> None:
    print(f'In {lambda_function} test were used: {params}')


def _get_db_connection():
    database_credentials = secrets.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
    username = json.loads(database_credentials['SecretString'])['username']
    password = json.loads(database_credentials['SecretString'])['password']
    host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'

    connection_string = f"host={host} dbname='sracollector' user='{username}' password='{password}'"
    print('DB connection ready :)')
    return psycopg2.connect(connection_string)
