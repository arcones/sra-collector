import json

import boto3
import botocore
import pytest

from ..utils_test import _provide_random_request_id
from ..utils_test import _sqs_wrap
from .utils_integration_test import _store_test_request
from .utils_integration_test import _wait_test_server_readiness
from .utils_integration_test import PostgreConnectionManager


@pytest.fixture(scope='session', autouse=True)
def init_tests():
    _wait_test_server_readiness()

# todo OTRO VALOR AÑADIDO DE ESTOS TESTS ES METERLE AQUI VARIOS MENSAJES DE ENTRADA


@pytest.fixture(scope='session', autouse=True)
def lambda_client():
    botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=360, retries={'max_attempts': 0})
    lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)
    yield lambda_client
    lambda_client.close()


def test_a_get_user_query(lambda_client):
    # GIVEN
    payload = json.dumps({'ncbi_query': 'mock query'})  # TODO consider add A_ lambda body load to general utils

    with open(f'tests/fixtures/A_get_user_query_input.json') as json_data:
        input_body = json.load(json_data)
        input_body['requestContext']['requestId'] = 'mockRequest'
        input_body['body'] = payload

    # WHEN
    invocation_result = lambda_client.invoke(FunctionName='A_get_user_query', Payload=json.dumps(input_body))

    # THEN
    lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

    assert lambda_response['statusCode'] == 201
    assert json.loads(lambda_response['body']) == {'request_id': 'mockRequest', 'ncbi_query': 'mock query'}
    assert lambda_response['headers'] == {'content-type': 'application/json'}


def test_b_get_query_pages(lambda_client):
    # GIVEN
    input_body = json.dumps({'request_id': _provide_random_request_id(), 'ncbi_query': 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS'})

    # WHEN
    invocation_result = lambda_client.invoke(FunctionName='B_get_query_pages', Payload=_sqs_wrap([input_body], dumps=True))

    # THEN
    lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

    assert lambda_response['batchItemFailures'] == []


def test_c_get_study_ids(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id = _provide_random_request_id()
        input_body = json.dumps({'request_id': request_id, 'retstart': 0, 'retmax': 500})
        _store_test_request((database_connection, database_cursor), request_id, 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS')

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='C_get_study_ids', Payload=_sqs_wrap([input_body], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert lambda_response['batchItemFailures'] == []



# def test_d_get_study_geo():
#     pass
#
#
# def test_e_get_study_srp():
#     pass
#
#
# def test_f_get_study_srrs():
#     pass
