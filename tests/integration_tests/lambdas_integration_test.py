import json

import boto3
import botocore
import pytest

from ..utils_test import _apigateway_wrap
from ..utils_test import provide_random_request_id
from ..utils_test import sqs_wrap
from .utils_integration_test import delete_test_request
from .utils_integration_test import PostgreConnectionManager
from .utils_integration_test import store_test_geo_study
from .utils_integration_test import store_test_request
from .utils_integration_test import store_test_sra_project
from .utils_integration_test import store_test_sra_run
from .utils_integration_test import store_test_sra_run_metadata
from .utils_integration_test import stores_test_ncbi_study
from .utils_integration_test import wait_test_server_readiness


@pytest.fixture(scope='session', autouse=True)
def init_tests():
    wait_test_server_readiness()


@pytest.fixture(scope='session', autouse=True)
def lambda_client():
    botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=360, retries={'max_attempts': 0})
    lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)
    yield lambda_client
    lambda_client.close()


@pytest.fixture(scope='session', autouse=True)
def cognito_credentials():
    secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
    cognito_credentials_secret = secrets_client.get_secret_value(SecretId='integration_test_credentials')
    cognito_username = json.loads(cognito_credentials_secret['SecretString'])['username']
    cognito_password = json.loads(cognito_credentials_secret['SecretString'])['password']
    yield {'username': cognito_username, 'password': cognito_password}


def test_a_get_user_query(lambda_client, cognito_credentials):
    # GIVEN
    input_body = _apigateway_wrap('mockRequest', {'ncbi_query': 'mock query'}, cognito_credentials['username'], cognito_credentials['password'], dumps=True)

    # WHEN
    invocation_result = lambda_client.invoke(FunctionName='A_get_user_query', Payload=input_body)

    # THEN
    lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

    assert 'errorMessage' not in lambda_response
    assert 'errorType' not in lambda_response

    assert lambda_response['statusCode'] == 201
    assert json.loads(lambda_response['body']) == {'request_id': 'mockRequest', 'ncbi_query': 'mock query'}
    assert lambda_response['headers'] == {'content-type': 'application/json'}


def test_b_get_query_pages(lambda_client):
    # GIVEN
    input_body_1 = json.dumps({'request_id': provide_random_request_id(), 'ncbi_query': 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS', 'mail': 'tomasa@grijander.com'})
    input_body_2 = json.dumps({'request_id': provide_random_request_id(), 'ncbi_query': 'stroke AND single cell rna seq AND musculus', 'mail': 'lauria@arcrolo.com'})

    # WHEN
    invocation_result = lambda_client.invoke(FunctionName='B_get_query_pages', Payload=sqs_wrap([input_body_1, input_body_2], dumps=True))

    # THEN
    lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

    assert 'errorMessage' not in lambda_response
    assert 'errorType' not in lambda_response

    assert lambda_response['batchItemFailures'] == []


def test_c_get_study_ids(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id_1 = provide_random_request_id()
        input_body_1 = json.dumps({'request_id': request_id_1, 'retstart': 0, 'retmax': 500})
        store_test_request((database_connection, database_cursor), request_id_1, 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS')

        request_id_2 = provide_random_request_id()
        input_body_2 = json.dumps({'request_id': request_id_2, 'retstart': 0, 'retmax': 500})
        store_test_request((database_connection, database_cursor), request_id_2, 'stroke AND single cell rna seq AND musculus')

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='C_get_study_ids', Payload=sqs_wrap([input_body_1, input_body_2], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert 'errorMessage' not in lambda_response
        assert 'errorType' not in lambda_response

        assert lambda_response['batchItemFailures'] == []


def test_d_get_study_geo(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id_1 = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id_1, 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS')
        ncbi_study_id_1 = stores_test_ncbi_study((database_connection, database_cursor), request_id_1, 200126815)
        input_body_1 = json.dumps({'ncbi_study_id': ncbi_study_id_1})

        request_id_2 = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id_2, 'stroke AND single cell rna seq AND musculus')
        ncbi_study_id_2 = stores_test_ncbi_study((database_connection, database_cursor), request_id_2, 200069235)
        input_body_2 = json.dumps({'ncbi_study_id': ncbi_study_id_2})

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='D_get_study_geo', Payload=sqs_wrap([input_body_1, input_body_2], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert lambda_response is None or 'errorMessage' not in lambda_response
        assert lambda_response is None or 'errorType' not in lambda_response


def test_e_get_study_srp(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id_1 = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id_1, 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS')
        ncbi_study_id_1 = stores_test_ncbi_study((database_connection, database_cursor), request_id_1, 200126815)
        geo_entity_id_1 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_1, 'GSE126815')
        input_body_1 = json.dumps({'geo_entity_id': geo_entity_id_1})

        request_id_2 = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id_2, 'stroke AND single cell rna seq AND musculus')
        ncbi_study_id_2 = stores_test_ncbi_study((database_connection, database_cursor), request_id_2, 200069235)
        geo_entity_id_2 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_2, 'GSE069235')
        input_body_2 = json.dumps({'geo_entity_id': geo_entity_id_2})

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='E_get_study_srp', Payload=sqs_wrap([input_body_1, input_body_2], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert lambda_response is None or 'errorMessage' not in lambda_response
        assert lambda_response is None or 'errorType' not in lambda_response

        assert lambda_response['batchItemFailures'] == []


def test_f_get_study_srrs(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id_1 = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id_1, 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS')
        ncbi_study_id_1 = stores_test_ncbi_study((database_connection, database_cursor), request_id_1, 200126815)
        geo_entity_id_1 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_1, 'GSE126815')
        sra_project_id_1 = store_test_sra_project((database_connection, database_cursor), geo_entity_id_1, 'SRP185522')
        input_body_1 = json.dumps({'sra_project_id': sra_project_id_1})

        request_id_2 = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id_2, 'stroke AND single cell rna seq AND musculus')
        ncbi_study_id_2 = stores_test_ncbi_study((database_connection, database_cursor), request_id_2, 200069235)
        geo_entity_id_2 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_2, 'GSE069235')
        sra_project_id_2 = store_test_sra_project((database_connection, database_cursor), geo_entity_id_2, 'SRP421048')
        input_body_2 = json.dumps({'sra_project_id': sra_project_id_2})

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='F_get_study_srrs', Payload=sqs_wrap([input_body_1, input_body_2], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert lambda_response is None or 'errorMessage' not in lambda_response
        assert lambda_response is None or 'errorType' not in lambda_response

        assert lambda_response['batchItemFailures'] == []


def test_g_get_srr_metadata(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id, 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS')

        ncbi_study_id_1 = stores_test_ncbi_study((database_connection, database_cursor), request_id, 200126815)
        ncbi_study_id_2 = stores_test_ncbi_study((database_connection, database_cursor), request_id, 200069235)

        geo_entity_id_1 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_1, 'GSE126815')
        geo_entity_id_2 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_2, 'GSE069235')

        sra_project_id_1 = store_test_sra_project((database_connection, database_cursor), geo_entity_id_1, 'SRP185522')
        sra_project_id_2 = store_test_sra_project((database_connection, database_cursor), geo_entity_id_2, 'SRP421048')

        sra_run_id_1 = store_test_sra_run((database_connection, database_cursor), sra_project_id_1, 'SRR22873806')
        sra_run_id_2 = store_test_sra_run((database_connection, database_cursor), sra_project_id_2, 'SRR18507358')

        input_body_1 = json.dumps({'sra_run_id': sra_run_id_1})
        input_body_2 = json.dumps({'sra_run_id': sra_run_id_2})

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='G_get_srr_metadata', Payload=sqs_wrap([input_body_1, input_body_2], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert lambda_response is None or 'errorMessage' not in lambda_response
        assert lambda_response is None or 'errorType' not in lambda_response

        assert lambda_response['batchItemFailures'] == []


def test_h_generate_report(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id = provide_random_request_id()
        store_test_request((database_connection, database_cursor), request_id, 'multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS')

        ncbi_study_id_1 = stores_test_ncbi_study((database_connection, database_cursor), request_id, 200126815)
        ncbi_study_id_2 = stores_test_ncbi_study((database_connection, database_cursor), request_id, 200069235)

        geo_entity_id_1 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_1, 'GSE126815')
        geo_entity_id_2 = store_test_geo_study((database_connection, database_cursor), ncbi_study_id_2, 'GSE069235')

        sra_project_id_1 = store_test_sra_project((database_connection, database_cursor), geo_entity_id_1, 'SRP185522')
        sra_project_id_2 = store_test_sra_project((database_connection, database_cursor), geo_entity_id_2, 'SRP421048')

        sra_run_id_1 = store_test_sra_run((database_connection, database_cursor), sra_project_id_1, 'SRR22873806')
        sra_run_id_2 = store_test_sra_run((database_connection, database_cursor), sra_project_id_2, 'SRR18507358')

        store_test_sra_run_metadata((database_connection, database_cursor), sra_run_id_1)
        store_test_sra_run_metadata((database_connection, database_cursor), sra_run_id_2)

        input_body = json.dumps({'request_id': request_id})

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='H_generate_report', Payload=sqs_wrap([input_body], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert lambda_response is None or 'errorMessage' not in lambda_response
        assert lambda_response is None or 'errorType' not in lambda_response

        assert lambda_response['batchItemFailures'] == []


def test_i_send_email(lambda_client):
    with PostgreConnectionManager() as (database_connection, database_cursor):
        # GIVEN
        request_id = 'integration_test'
        delete_test_request((database_connection, database_cursor))
        store_test_request((database_connection, database_cursor), request_id, 'whatever')

        input_body = json.dumps({'request_id': request_id, 'filename': f'Report_{request_id}.csv'})

        # WHEN
        invocation_result = lambda_client.invoke(FunctionName='I_send_email', Payload=sqs_wrap([input_body], dumps=True))

        # THEN
        lambda_response = json.loads(invocation_result['Payload']._raw_stream.data.decode('utf-8'))

        assert lambda_response is None or 'errorMessage' not in lambda_response
        assert lambda_response is None or 'errorType' not in lambda_response

        assert lambda_response['batchItemFailures'] == []
