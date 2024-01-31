import json
import random
import string
import time

import boto3
import botocore
import urllib3

LAMBDA_TIMEOUT = 90

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits

botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=LAMBDA_TIMEOUT, retries={'max_attempts': 0})

lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)

http = urllib3.PoolManager()


def _init_tests():
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
    _init_tests()
    lambda_function = 'A_get_user_query'

    expected_request_id = ''.join(random.choice(CHARACTERS) for i in range(20))
    expected_ncbi_query = ''.join(random.choice(CHARACTERS) for i in range(50))
    expected_body = json.dumps({'ncbi_query': expected_ncbi_query}).replace('"', '\"')

    with open(f'tests/fixtures/{lambda_function}_input.json') as json_data:
        payload = json.load(json_data)
        payload['requestContext']['requestId'] = expected_request_id
        payload['body'] = expected_body
        response = lambda_client.invoke(FunctionName=lambda_function, Payload=json.dumps(payload))

    actual_response = json.loads(response['Payload'].read())

    actual_response_status = actual_response['statusCode']
    actual_response_payload = actual_response['body']

    assert actual_response_status == 201
    assert actual_response_payload == f'{{"request_id": "{expected_request_id}", "ncbi_query": "{expected_ncbi_query}"}}'
