import json

import boto3
import botocore
import pytest
from utils_test import _wait_test_server_readiness


@pytest.fixture(scope='session', autouse=True)
def init_tests():
    _wait_test_server_readiness()


@pytest.fixture(scope='session', autouse=True)
def lambda_client():
    botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=360, retries={'max_attempts': 0})
    lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)
    yield lambda_client
    lambda_client.close()


def test_a_get_user_query(lambda_client):
    input_body = json.dumps({'ncbi_query': 'mock query'})

    with open(f'tests/integration_tests/fixtures/A_get_user_query_input.json') as json_data:
        payload = json.load(json_data)
        payload['requestContext']['requestId'] = 'mockRequest'
        payload['body'] = input_body

    response = lambda_client.invoke(FunctionName='A_get_user_query', Payload=json.dumps(payload))


def test_b_get_query_pages():
    pass


def test_c_get_study_ids():
    pass


def test_d_get_study_geo():
    pass


def test_e_get_study_srp():
    pass


def test_f_get_study_srrs():
    pass
