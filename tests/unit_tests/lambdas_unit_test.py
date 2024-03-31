import json
import os
import re
import sys
from unittest.mock import ANY
from unittest.mock import call
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from ..utils_test import _apigateway_wrap
from ..utils_test import provide_random_request_id
from ..utils_test import sqs_wrap
from .utils_unit_test import Context
from .utils_unit_test import DEFAULT_FIXTURE
from .utils_unit_test import H2ConnectionManager
from .utils_unit_test import mock_eutils
from .utils_unit_test import mock_pysradb
from .utils_unit_test import store_test_geo_study
from .utils_unit_test import store_test_metadata
from .utils_unit_test import store_test_request
from .utils_unit_test import store_test_sra_project
from .utils_unit_test import store_test_sra_run
from .utils_unit_test import stores_test_ncbi_study

os.environ['ENV'] = 'unit-test'

sys.path.append('infra/lambdas/code')
import A_get_user_query
import B_get_query_pages
import C_get_study_ids
import D_get_study_geo
import E_get_study_srp
import F_get_study_srrs
import G_get_srr_metadata
import H_generate_report


def test_a_get_user_query():
    with patch.object(A_get_user_query, 'sqs') as mock_sqs:
        with patch.object(A_get_user_query.cognito, 'initiate_auth') as mock_cognito:
            # GIVEN
            request_id = provide_random_request_id()

            mock_sqs.send_message = Mock()
            mock_cognito.return_value = {'AuthenticationResult': {'foo': 'bar'}}

            input_body = _apigateway_wrap(request_id, {'ncbi_query': DEFAULT_FIXTURE['query_<20']}, user=DEFAULT_FIXTURE['mail'], password='correct_password')

            # WHEN
            actual_result = A_get_user_query.handler(input_body, Context('A_get_user_query'))

            # THEN REGARDING LAMBDA
            assert actual_result['statusCode'] == 201
            assert actual_result['body'] == f'{{"request_id": "{request_id}", "ncbi_query": "{DEFAULT_FIXTURE["query_<20"]}"}}'

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 1
            mock_sqs.send_message.assert_called_with(QueueUrl=ANY, MessageBody=json.dumps(
                {'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query_<20'], 'mail': DEFAULT_FIXTURE['mail']}))


def test_a_get_user_query_bad_credentials():
    with patch.object(A_get_user_query, 'sqs') as mock_sqs:
        with patch.object(A_get_user_query.cognito, 'initiate_auth') as mock_cognito:
            # GIVEN
            request_id = provide_random_request_id()

            mock_sqs.send_message = Mock()
            mock_cognito.side_effect = ClientError({'Error': {'Code': 'UserNotFoundException', 'Message': 'User not found'}}, 'operation_name')

            input_body = _apigateway_wrap(request_id, {'ncbi_query': DEFAULT_FIXTURE['query_<20']}, user='not_registered_user@caca.com', password='wrong_password')

            # WHEN
            actual_result = A_get_user_query.handler(input_body, Context('A_get_user_query'))

            # THEN REGARDING LAMBDA
            assert actual_result['statusCode'] == 401
            assert 'body' not in actual_result

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 0


def test_b_get_query_pages():
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs:
        with patch.object(B_get_query_pages.http, 'request', side_effect=mock_eutils):
            with H2ConnectionManager() as (database_connection, database_cursor):
                # GIVEN
                request_id = provide_random_request_id()

                mock_sqs.send_message_batch = Mock()

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query_+500'], 'mail': DEFAULT_FIXTURE['mail']})

                # WHEN
                actual_result = B_get_query_pages.handler(sqs_wrap([input_body]), Context('B_get_query_pages'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                database_cursor.execute(f"select id, query, geo_count, mail from request where id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                expected_row = [(request_id, DEFAULT_FIXTURE['query_+500'], DEFAULT_FIXTURE['results'], DEFAULT_FIXTURE['mail'])]
                assert actual_rows == expected_row

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message_batch.call_count == 1

                actual_message_bodies = [json.loads(entry['MessageBody']) for entry in mock_sqs.send_message_batch.call_args_list[0].kwargs['Entries']]
                assert {message_body['request_id'] for message_body in actual_message_bodies} == {request_id}
                assert {message_body['retmax'] for message_body in actual_message_bodies} == {500}
                assert {message_body['retstart'] for message_body in actual_message_bodies} == {0, 500}


def test_b_get_query_pages_skip_already_processed_study_id():
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs:
        with patch.object(B_get_query_pages.http, 'request', side_effect=mock_eutils):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()

                mock_sqs.send_message_batch = Mock()

                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_+500'])

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query_+500'], 'mail': DEFAULT_FIXTURE['mail']})

                # WHEN
                actual_result = B_get_query_pages.handler(sqs_wrap([input_body]), Context('B_get_query_pages'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f"select id from request where id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                assert actual_rows == [(request_id,)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_b_get_query_pages_stop_expensive_queries():
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs:
        with patch.object(B_get_query_pages.http, 'request', side_effect=mock_eutils):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()

                mock_sqs.send_message = Mock()

                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_over_limit'])

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query_over_limit'], 'mail': DEFAULT_FIXTURE['mail']})

                # WHEN
                actual_result = B_get_query_pages.handler(sqs_wrap([input_body]), Context('B_get_query_pages'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f"select id from request where id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                assert actual_rows == [(request_id,)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 1
                expected_reason = (f'Queries with more than 1000 studies cannot be processed as costs are not affordable.'
                                   f"Check how many studies has your query in https://www.ncbi.nlm.nih.gov/gds/?term={DEFAULT_FIXTURE['query_over_limit']}"
                                   'Do smaller queries or contact webmaster marta.arcones@gmail.com to see alternatives')
                mock_sqs.send_message.assert_called_with(QueueUrl=ANY, MessageBody=json.dumps({'request_id': request_id, 'result': 'FAILURE', 'reason': expected_reason}))


def test_c_get_study_ids():
    with patch.object(C_get_study_ids, 'sqs') as mock_sqs:
        with patch.object(C_get_study_ids.http, 'request', side_effect=mock_eutils):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()

                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])

                mock_sqs.send_message_batch = Mock()

                input_body = json.dumps({'request_id': request_id, 'retstart': 0, 'retmax': 500})

                # WHEN
                actual_result = C_get_study_ids.handler(sqs_wrap([input_body]), Context('C_get_study_ids'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}' order by ncbi_id")
                actual_rows = database_cursor.fetchall()
                expected_study_ids = [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391]
                assert actual_rows == [(study_id, request_id, None) for study_id in expected_study_ids]

                # THEN REGARDING MESSAGES
                database_cursor.execute(f"select id from ncbi_study where request_id='{request_id}'")
                ncbi_study_ids = database_cursor.fetchall()

                assert mock_sqs.send_message_batch.call_count == 1

                expected_message_bodies = [{'ncbi_study_id': ncbi_study_id[0]} for ncbi_study_id in ncbi_study_ids]
                actual_message_bodies = [json.loads(entry['MessageBody']) for entry in mock_sqs.send_message_batch.call_args_list[0].kwargs['Entries']]
                assert actual_message_bodies == expected_message_bodies


def test_d_get_study_geos_gse():
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request', side_effect=mock_eutils):
                with H2ConnectionManager() as database_holder:
                    # GIVEN
                    request_id = provide_random_request_id()

                    store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                    ncbi_study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])

                    mock_sqs.send_message = Mock()
                    mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}

                    input_body = json.dumps({'ncbi_study_id': ncbi_study_id})

                    # WHEN
                    D_get_study_geo.handler(sqs_wrap([input_body]), Context('D_get_study_geo'))

                    # THEN REGARDING DATA
                    _, database_cursor = database_holder
                    database_cursor.execute(f"select ncbi_study_id, gse from geo_study where ncbi_study_id='{ncbi_study_id}'")
                    actual_geo_study_row = database_cursor.fetchall()
                    assert actual_geo_study_row == [(ncbi_study_id, DEFAULT_FIXTURE['gse'])]

                    database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}'")
                    actual_ncbi_study_row = database_cursor.fetchall()
                    assert actual_ncbi_study_row == [(DEFAULT_FIXTURE['ncbi_id'], request_id, None)]

                    # THEN REGARDING MESSAGES
                    database_cursor.execute(f"select id from geo_study where ncbi_study_id='{ncbi_study_id}'")
                    geo_study_id = database_cursor.fetchall()[0][0]
                    assert mock_sqs.send_message.call_count == 1
                    mock_sqs.send_message.assert_called_with(QueueUrl=ANY, MessageBody=json.dumps({'geo_entity_id': geo_study_id}))


@pytest.mark.parametrize('ncbi_id, geo_table, geo_entity_name, geo_entity_value, geo_fixture', [
    (305668979, 'geo_experiment', 'gsm', 'GSM5668979', 'D_get_study_geo_mocked_esummary_gsm.json'),
    (100019750, 'geo_platform', 'gpl', 'GPL19750', 'D_get_study_geo_mocked_esummary_gpl.json'),
    (3268, 'geo_data_set', 'gds', 'GDS3268', 'D_get_study_geo_mocked_esummary_gds.json'),
])
def test_d_get_study_geos_not_gse(ncbi_id, geo_table, geo_entity_name, geo_entity_value, geo_fixture):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request', side_effect=mock_eutils):
                with H2ConnectionManager() as database_holder:
                    # GIVEN
                    request_id = provide_random_request_id()

                    store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                    ncbi_study_id = stores_test_ncbi_study(database_holder, request_id, ncbi_id)

                    mock_sqs.send_message = Mock()
                    mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}

                    input_body = json.dumps({'ncbi_study_id': ncbi_study_id})

                    # WHEN
                    D_get_study_geo.handler(sqs_wrap([input_body]), Context('D_get_study_geo'))

                    # THEN REGARDING DATA
                    _, database_cursor = database_holder
                    database_cursor.execute(f"select ncbi_study_id, {geo_entity_name} from {geo_table} where ncbi_study_id='{ncbi_study_id}'")
                    actual_geo_entity_row = database_cursor.fetchall()
                    assert actual_geo_entity_row == [(ncbi_study_id, geo_entity_value)]

                    database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}'")
                    actual_ncbi_study_row = database_cursor.fetchall()
                    assert actual_ncbi_study_row == [(ncbi_id, request_id, 0)]

                    # THEN REGARDING MESSAGES
                    assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_ok():
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp', side_effect=mock_pysradb):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()

                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])

                mock_sqs.send_message = Mock()

                input_body = json.dumps({'geo_entity_id': inserted_geo_study_id})

                # WHEN
                actual_result = E_get_study_srp.handler(sqs_wrap([input_body]), Context('E_get_study_srp'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select sp.* from sra_project sp where geo_study_id={inserted_geo_study_id}')
                actual_srp_rows = database_cursor.fetchall()
                sra_project_id = actual_srp_rows[0][0]
                assert actual_srp_rows[0][1] == DEFAULT_FIXTURE['srp']

                database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}'")
                actual_ncbi_study_row = database_cursor.fetchall()
                assert actual_ncbi_study_row == [(DEFAULT_FIXTURE['ncbi_id'], request_id, None)]

                database_cursor.execute(f'select * from sra_project_missing where geo_study_id={inserted_geo_study_id}')
                actual_ko_rows = database_cursor.fetchall()
                assert actual_ko_rows == []

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 1
                expected_calls = [call(QueueUrl=ANY, MessageBody=json.dumps({'sra_project_id': sra_project_id}))]
                actual_calls = mock_sqs.send_message.call_args_list

                assert expected_calls == actual_calls


@pytest.mark.parametrize('pysradb_exception, pysradb_exception_info, pysradb_exception_name', [
    (AttributeError, 'jander', 'ATTRIBUTE_ERROR'),
    (ValueError, 'clander', 'VALUE_ERROR'),
    (KeyError, 'crispin', 'KEY_ERROR')
])
def test_e_get_study_srp_known_error(pysradb_exception, pysradb_exception_info, pysradb_exception_name):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()

                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])

                mock_sqs.send_message = Mock()
                mock_sra_web_gse_to_srp.side_effect = pysradb_exception(pysradb_exception_info)

                input_body = json.dumps({'geo_entity_id': inserted_geo_study_id})

                # WHEN
                actual_result = E_get_study_srp.handler(sqs_wrap([input_body]), Context('E_get_study_srp'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select srp from sra_project where geo_study_id={inserted_geo_study_id}')
                actual_ok_rows = database_cursor.fetchall()
                assert actual_ok_rows == []

                database_cursor.execute(
                    f'select pysradb_error_reference_id, details from sra_project_missing where geo_study_id={inserted_geo_study_id}')
                actual_ko_rows = database_cursor.fetchall()[0]
                database_cursor.execute(f"select id from pysradb_error_reference where operation='gse_to_srp' and name='{pysradb_exception_name}'")
                pysradb_error_reference_id = database_cursor.fetchone()[0]
                assert actual_ko_rows[0] == pysradb_error_reference_id
                assert re.match(rf"'?{pysradb_exception_info}'?", actual_ko_rows[1])

                database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}'")
                actual_ncbi_study_row = database_cursor.fetchall()
                assert actual_ncbi_study_row == [(DEFAULT_FIXTURE['ncbi_id'], request_id, 0)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_skip_unexpected_results():
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()
                unexpected_srp = 'DRP010911'

                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])

                mock_sqs.send_message = Mock()
                mock_sra_web_gse_to_srp.return_value = {'study_accession': [unexpected_srp]}

                input_body = json.dumps({'geo_entity_id': inserted_geo_study_id})

                # WHEN
                actual_result = E_get_study_srp.handler(sqs_wrap([input_body]), Context('E_get_study_srp'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select srp from sra_project where geo_study_id={inserted_geo_study_id}')
                actual_ok_rows = database_cursor.fetchall()
                assert actual_ok_rows == []

                database_cursor.execute(f'select * from sra_project_missing where geo_study_id={inserted_geo_study_id}')
                actual_ko_rows = database_cursor.fetchall()
                assert actual_ko_rows == []

                database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}'")
                actual_ncbi_study_row = database_cursor.fetchall()
                assert actual_ncbi_study_row == [(DEFAULT_FIXTURE['ncbi_id'], request_id, 0)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_f_get_study_srrs_ok():
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr', side_effect=mock_pysradb):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()
                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])
                inserted_sra_project_id = store_test_sra_project(database_holder, inserted_geo_study_id, DEFAULT_FIXTURE['srp'])

                mock_sqs.send_message_batch = Mock()

                input_body = json.dumps({'sra_project_id': inserted_sra_project_id})

                # WHEN
                actual_result = F_get_study_srrs.handler(sqs_wrap([input_body]), Context('F_get_study_srrs'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select * from sra_run where sra_project_id={inserted_sra_project_id}')
                actual_ok_rows = database_cursor.fetchall()
                actual_srrs = [actual_ok_row[1] for actual_ok_row in actual_ok_rows]
                assert actual_srrs == DEFAULT_FIXTURE['srrs']

                database_cursor.execute(f'select * from sra_run_missing where sra_project_id={inserted_sra_project_id}')
                actual_ko_rows = database_cursor.fetchall()
                assert actual_ko_rows == []

                database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}'")
                actual_ncbi_study_row = database_cursor.fetchall()
                assert actual_ncbi_study_row == [(DEFAULT_FIXTURE['ncbi_id'], request_id, 2)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message_batch.call_count == 1

                expected_message_bodies = [{'sra_run_id': srr_row[0]} for srr_row in actual_ok_rows]
                actual_message_bodies = [json.loads(entry['MessageBody']) for entry in mock_sqs.send_message_batch.call_args_list[0].kwargs['Entries']]

                assert actual_message_bodies == expected_message_bodies


@pytest.mark.parametrize('pysradb_exception, pysradb_exception_info, pysradb_exception_name', [
    (AttributeError, 'jander', 'ATTRIBUTE_ERROR'),
    (TypeError, 'clander', 'TYPE_ERROR')
])
def test_f_get_study_srrs_ko(pysradb_exception, pysradb_exception_info, pysradb_exception_name):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr') as mock_sra_web_srp_to_srr:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()

                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])
                inserted_sra_project_id = store_test_sra_project(database_holder, inserted_geo_study_id, DEFAULT_FIXTURE['srp'])

                mock_sqs.send_message_batch = Mock()
                mock_sra_web_srp_to_srr.side_effect = pysradb_exception(pysradb_exception_info)

                input_body = json.dumps({'sra_project_id': inserted_sra_project_id})

                # WHEN
                actual_result = F_get_study_srrs.handler(sqs_wrap([input_body]), Context('F_get_study_srrs'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select srr from sra_run where sra_project_id={inserted_sra_project_id}')
                actual_ok_rows = database_cursor.fetchall()
                assert actual_ok_rows == []

                database_cursor.execute(f'select pysradb_error_reference_id, details from sra_run_missing where sra_project_id={inserted_sra_project_id}')
                actual_ko_rows = database_cursor.fetchall()
                database_cursor.execute(f"select id from pysradb_error_reference where operation='srp_to_srr' and name='{pysradb_exception_name}'")
                pysradb_error_reference_id = database_cursor.fetchone()[0]
                assert actual_ko_rows == [(pysradb_error_reference_id, pysradb_exception_info)]

                database_cursor.execute(f"select ncbi_id, request_id, srr_metadata_count from ncbi_study where request_id='{request_id}'")
                actual_ncbi_study_row = database_cursor.fetchall()
                assert actual_ncbi_study_row == [(DEFAULT_FIXTURE['ncbi_id'], request_id, 0)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message_batch.call_count == 0


def test_g_get_srr_metadata_start():
    with patch.object(G_get_srr_metadata, 'sqs') as mock_sqs:
        with patch.object(G_get_srr_metadata.http, 'request', side_effect=mock_eutils):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()
                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])
                inserted_sra_project_id = store_test_sra_project(database_holder, inserted_geo_study_id, DEFAULT_FIXTURE['srp'])
                inserted_sra_run_id = store_test_sra_run(database_holder, inserted_sra_project_id, DEFAULT_FIXTURE['srrs'][0])

                mock_sqs.send_message = Mock()

                input_body = json.dumps({'sra_run_id': inserted_sra_run_id})

                # WHEN
                actual_result = G_get_srr_metadata.handler(sqs_wrap([input_body]), Context('G_get_srr_metadata'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select * from sra_run_metadata where sra_run_id={inserted_sra_run_id}')
                actual_sra_run_metadata_rows = database_cursor.fetchone()
                srr_metadata_id = actual_sra_run_metadata_rows[0]
                assert actual_sra_run_metadata_rows[2] == DEFAULT_FIXTURE['metadatas'][0]['spots']
                assert actual_sra_run_metadata_rows[3] == DEFAULT_FIXTURE['metadatas'][0]['bases']
                assert actual_sra_run_metadata_rows[4] == DEFAULT_FIXTURE['metadatas'][0]['organism']

                database_cursor.execute(f'select * from sra_run_metadata_phred where sra_run_metadata_id={srr_metadata_id}')
                actual_phred_rows = database_cursor.fetchall()
                actual_phred_rows_payload = [(actual_phred_row[2], actual_phred_row[3]) for actual_phred_row in actual_phred_rows]
                assert actual_phred_rows_payload == DEFAULT_FIXTURE['metadatas'][0]['phred']

                database_cursor.execute(f'select * from sra_run_metadata_statistic_read where sra_run_metadata_id={srr_metadata_id}')
                statistic_read = database_cursor.fetchone()
                statistic_read_id = statistic_read[0]
                assert statistic_read[2] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['nspots']
                assert statistic_read[3] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['layout']
                assert statistic_read[4] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_count']
                assert statistic_read[5] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_average']
                assert statistic_read[6] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_stdev']
                assert statistic_read[7] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_count']
                assert statistic_read[8] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_average']
                assert statistic_read[9] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_stdev']

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_g_get_srr_metadata_finish():
    with patch.object(G_get_srr_metadata, 'sqs') as mock_sqs:
        with patch.object(G_get_srr_metadata.http, 'request', side_effect=mock_eutils):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()
                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], 2)
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])
                inserted_sra_project_id = store_test_sra_project(database_holder, inserted_geo_study_id, DEFAULT_FIXTURE['srp'])
                inserted_sra_run_id = store_test_sra_run(database_holder, inserted_sra_project_id, DEFAULT_FIXTURE['srrs'][0])

                mock_sqs.send_message = Mock()

                input_body = json.dumps({'sra_run_id': inserted_sra_run_id})

                # WHEN
                actual_result = G_get_srr_metadata.handler(sqs_wrap([input_body]), Context('G_get_srr_metadata'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select * from sra_run_metadata where sra_run_id={inserted_sra_run_id}')
                actual_sra_run_metadata_rows = database_cursor.fetchone()
                srr_metadata_id = actual_sra_run_metadata_rows[0]
                assert actual_sra_run_metadata_rows[2] == DEFAULT_FIXTURE['metadatas'][0]['spots']
                assert actual_sra_run_metadata_rows[3] == DEFAULT_FIXTURE['metadatas'][0]['bases']
                assert actual_sra_run_metadata_rows[4] == DEFAULT_FIXTURE['metadatas'][0]['organism']

                database_cursor.execute(f'select * from sra_run_metadata_phred where sra_run_metadata_id={srr_metadata_id}')
                actual_phred_rows = database_cursor.fetchall()
                actual_phred_rows_payload = [(actual_phred_row[2], actual_phred_row[3]) for actual_phred_row in actual_phred_rows]
                assert actual_phred_rows_payload == DEFAULT_FIXTURE['metadatas'][0]['phred']

                database_cursor.execute(f'select * from sra_run_metadata_statistic_read where sra_run_metadata_id={srr_metadata_id}')
                statistic_read = database_cursor.fetchone()
                statistic_read_id = statistic_read[0]
                assert statistic_read[2] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['nspots']
                assert statistic_read[3] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['layout']
                assert statistic_read[4] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_count']
                assert statistic_read[5] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_average']
                assert statistic_read[6] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_stdev']
                assert statistic_read[7] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_count']
                assert statistic_read[8] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_average']
                assert statistic_read[9] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_stdev']

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 1
                mock_sqs.send_message.assert_called_with(QueueUrl=ANY, MessageBody=json.dumps({'request_id': request_id}))


def test_h_generate_report():
    with patch.object(H_generate_report, 's3') as mock_s3:
        with patch('H_generate_report.csv.writer') as mock_csv_writer:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = provide_random_request_id()
                store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query_<20'])
                study_id = stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], 2)
                inserted_geo_study_id = store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])
                inserted_sra_project_id = store_test_sra_project(database_holder, inserted_geo_study_id, DEFAULT_FIXTURE['srp'])
                sra_run_id_1 = store_test_sra_run(database_holder, inserted_sra_project_id, DEFAULT_FIXTURE['srrs'][0])
                sra_run_id_2 = store_test_sra_run(database_holder, inserted_sra_project_id, DEFAULT_FIXTURE['srrs'][1])
                store_test_metadata(database_holder, [sra_run_id_1, sra_run_id_2])

                mock_s3.upload_file = Mock()
                mock_csv_writer_instance = mock_csv_writer.return_value

                input_body = json.dumps({'request_id': request_id})

                # WHEN
                actual_result = H_generate_report.handler(sqs_wrap([input_body]), Context('H_generate_report'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f"select status from request where id='{request_id}'")
                actual_request_status = database_cursor.fetchone()[0]
                assert actual_request_status == 'COMPLETED'

                # THEN REGARDING REPORT
                rows_written = mock_csv_writer_instance.writerows.call_args.args[0]

                assert rows_written[0][0] == rows_written[1][0] == request_id
                assert rows_written[0][1] == rows_written[1][1] == DEFAULT_FIXTURE['query_<20']
                assert rows_written[0][2] == rows_written[1][2] == DEFAULT_FIXTURE['ncbi_id']
                assert rows_written[0][3] == rows_written[1][3] == DEFAULT_FIXTURE['gse']
                assert rows_written[0][4] == rows_written[1][4] == DEFAULT_FIXTURE['srp']

                rows_written_for_first_srr = [row for row in rows_written if row[5] == DEFAULT_FIXTURE['srrs'][0]][0]
                rows_written_for_second_srr = [row for row in rows_written if row[5] == DEFAULT_FIXTURE['srrs'][1]][0]

                assert rows_written_for_first_srr[5] == DEFAULT_FIXTURE['srrs'][0]
                assert rows_written_for_first_srr[6] == DEFAULT_FIXTURE['metadatas'][0]['spots']
                assert rows_written_for_first_srr[7] == DEFAULT_FIXTURE['metadatas'][0]['bases']
                assert rows_written_for_first_srr[8] == DEFAULT_FIXTURE['metadatas'][0]['organism']
                assert rows_written_for_first_srr[9] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['nspots']
                assert rows_written_for_first_srr[10] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['layout']
                assert rows_written_for_first_srr[11] == 0.9196027757910978
                assert rows_written_for_first_srr[12] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_count']
                assert rows_written_for_first_srr[13] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_average']
                assert rows_written_for_first_srr[14] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_0_stdev']
                assert rows_written_for_first_srr[15] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_count']
                assert rows_written_for_first_srr[16] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_average']
                assert rows_written_for_first_srr[17] == DEFAULT_FIXTURE['metadatas'][0]['statistic_reads']['read_1_stdev']

                assert rows_written_for_second_srr[5] == DEFAULT_FIXTURE['srrs'][1]
                assert rows_written_for_second_srr[6] == DEFAULT_FIXTURE['metadatas'][1]['spots']
                assert rows_written_for_second_srr[7] == DEFAULT_FIXTURE['metadatas'][1]['bases']
                assert rows_written_for_second_srr[8] == DEFAULT_FIXTURE['metadatas'][1]['organism']
                assert rows_written_for_second_srr[9] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['nspots']
                assert rows_written_for_second_srr[10] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['layout']
                assert rows_written_for_second_srr[11] == 0.666666667
                assert rows_written_for_second_srr[12] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['read_0_count']
                assert rows_written_for_second_srr[13] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['read_0_average']
                assert rows_written_for_second_srr[14] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['read_0_stdev']
                assert rows_written_for_second_srr[15] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['read_1_count']
                assert rows_written_for_second_srr[16] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['read_1_average']
                assert rows_written_for_second_srr[17] == DEFAULT_FIXTURE['metadatas'][1]['statistic_reads']['read_1_stdev']

                # THEN REGARDING MESSAGES
                assert mock_s3.upload_file.call_count == 1
                expected_filename = f'Report_{request_id}.csv'
                mock_s3.upload_file.assert_called_with(f'/tmp/{expected_filename}', 'integration-tests-s3', expected_filename)
