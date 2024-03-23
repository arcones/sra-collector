import json
import os
import re
import sys
from unittest.mock import ANY
from unittest.mock import call
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from ..utils_test import _apigateway_wrap
from ..utils_test import _provide_random_request_id
from ..utils_test import _sqs_wrap
from .utils_unit_test import _check_link_and_srp_rows
from .utils_unit_test import _mock_eutils
from .utils_unit_test import _mock_pysradb
from .utils_unit_test import _store_test_geo_study
from .utils_unit_test import _store_test_request
from .utils_unit_test import _store_test_sra_project
from .utils_unit_test import _stores_test_ncbi_study
from .utils_unit_test import Context
from .utils_unit_test import DEFAULT_FIXTURE
from .utils_unit_test import H2ConnectionManager

os.environ['ENV'] = 'unit-test'

sys.path.append('infra/lambdas/code')
import A_get_user_query
import B_get_query_pages
import C_get_study_ids
import D_get_study_geo
import E_get_study_srp
import F_get_study_srrs


def test_a_get_user_query():
    with patch.object(A_get_user_query, 'sqs') as mock_sqs:
        # GIVEN
        request_id = _provide_random_request_id()

        mock_sqs.send_message = Mock()

        input_body = _apigateway_wrap(request_id, {'ncbi_query': DEFAULT_FIXTURE['query']})

        # WHEN
        actual_result = A_get_user_query.handler(input_body, Context('A_get_user_query'))

        # THEN REGARDING LAMBDA
        assert actual_result['statusCode'] == 201
        assert actual_result['body'] == f'{{"request_id": "{request_id}", "ncbi_query": "{DEFAULT_FIXTURE["query"]}"}}'

        # THEN REGARDING MESSAGES
        assert mock_sqs.send_message.call_count == 1
        mock_sqs.send_message.assert_called_with(QueueUrl=ANY, MessageBody=json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query']}))


def test_b_get_query_pages():
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs:
        with patch.object(B_get_query_pages.http, 'request', side_effect=_mock_eutils):
            with H2ConnectionManager() as (database_connection, database_cursor):
                # GIVEN
                request_id = _provide_random_request_id()

                mock_sqs.send_message_batch = Mock()

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query']})

                # WHEN
                actual_result = B_get_query_pages.handler(_sqs_wrap([input_body]), Context('B_get_query_pages'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                database_cursor.execute(f"select id, query, geo_count from request where id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                expected_row = [(request_id, DEFAULT_FIXTURE['query'], DEFAULT_FIXTURE['results'])]
                assert actual_rows == expected_row

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message_batch.call_count == 1

                actual_message_bodies = [json.loads(entry['MessageBody']) for entry in json.loads(mock_sqs.send_message_batch.call_args_list[0].kwargs['Entries'])]
                assert {message_body['request_id'] for message_body in actual_message_bodies} == {request_id}
                assert {message_body['retmax'] for message_body in actual_message_bodies} == {500}
                assert {message_body['retstart'] for message_body in actual_message_bodies} == {0, 500, 1000}


def test_b_get_query_pages_skip_already_processed_study_id():
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs:
        with patch.object(B_get_query_pages.http, 'request', side_effect=_mock_eutils):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()

                mock_sqs.send_message_batch = Mock()

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query']})

                # WHEN
                actual_result = B_get_query_pages.handler(_sqs_wrap([input_body]), Context('B_get_query_pages'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f"select id from request where id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                assert actual_rows == [(request_id,)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_c_get_study_ids():
    with patch.object(C_get_study_ids, 'sqs') as mock_sqs:
        with patch.object(C_get_study_ids.http, 'request', side_effect=_mock_eutils):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])

                mock_sqs.send_message_batch = Mock()

                input_body = json.dumps({'request_id': request_id, 'retstart': 0, 'retmax': 500})

                # WHEN
                actual_result = C_get_study_ids.handler(_sqs_wrap([input_body]), Context('C_get_study_ids'))

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f"select ncbi_id, request_id from ncbi_study where request_id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                expected_study_ids = [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391]
                assert actual_rows == [(study_id, request_id) for study_id in expected_study_ids]

                # THEN REGARDING MESSAGES
                database_cursor.execute(f"select id from ncbi_study where request_id='{request_id}'")
                ncbi_study_ids = database_cursor.fetchall()

                assert mock_sqs.send_message_batch.call_count == 1

                expected_call = [f'{{"ncbi_study_id": {ncbi_study_id[0]}}}' for ncbi_study_id in ncbi_study_ids]
                expected_call.sort()
                actual_message_bodies = [json.loads(entry['MessageBody']) for entry in json.loads(mock_sqs.send_message_batch.call_args_list[0].kwargs['Entries'])]
                actual_message_bodies.sort()
                assert expected_call == actual_message_bodies


def test_d_get_study_geos_gse():
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request', side_effect=_mock_eutils):
                with H2ConnectionManager() as database_holder:
                    # GIVEN
                    request_id = _provide_random_request_id()

                    _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                    ncbi_study_id = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])

                    mock_sqs.send_message = Mock()
                    mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}

                    input_body = json.dumps({'ncbi_study_id': ncbi_study_id})

                    # WHEN
                    D_get_study_geo.handler(_sqs_wrap([input_body]), 'a context')

                    # THEN REGARDING DATA
                    _, database_cursor = database_holder
                    database_cursor.execute(f"select ncbi_study_id, gse from geo_study where ncbi_study_id='{ncbi_study_id}'")
                    actual_row = database_cursor.fetchall()
                    assert actual_row == [(ncbi_study_id, DEFAULT_FIXTURE['gse'])]

                    # THEN REGARDING MESSAGES
                    database_cursor.execute(f"select id from geo_study where ncbi_study_id='{ncbi_study_id}'")
                    geo_study_id = database_cursor.fetchall()[0][0]
                    assert mock_sqs.send_message.call_count == 1
                    mock_sqs.send_message.assert_called_with(
                        QueueUrl=D_get_study_geo.output_sqs,
                        MessageBody=json.dumps({'geo_entity_id': geo_study_id})
                    )


@pytest.mark.parametrize('ncbi_study_id, geo_table, geo_entity_name, geo_entity_value, geo_fixture', [
    (305668979, 'geo_experiment', 'gsm', 'GSM5668979', 'D_get_study_geo_mocked_esummary_gsm.json'),
    (100019750, 'geo_platform', 'gpl', 'GPL19750', 'D_get_study_geo_mocked_esummary_gpl.json'),
    (3268, 'geo_data_set', 'gds', 'GDS3268', 'D_get_study_geo_mocked_esummary_gds.json'),
])
def test_d_get_study_geos_not_gse(ncbi_study_id, geo_table, geo_entity_name, geo_entity_value, geo_fixture):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request', side_effect=_mock_eutils):
                with H2ConnectionManager() as database_holder:
                    # GIVEN
                    request_id = _provide_random_request_id()

                    _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                    ncbi_study_id = _stores_test_ncbi_study(database_holder, request_id, ncbi_study_id)

                    mock_sqs.send_message = Mock()
                    mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}

                    input_body = json.dumps({'ncbi_study_id': ncbi_study_id})

                    # WHEN
                    D_get_study_geo.handler(_sqs_wrap([input_body]), 'a context')

                    # THEN REGARDING DATA
                    _, database_cursor = database_holder
                    database_cursor.execute(f"select ncbi_study_id, {geo_entity_name} from {geo_table} where ncbi_study_id='{ncbi_study_id}'")
                    actual_row = database_cursor.fetchall()
                    assert actual_row == [(ncbi_study_id, geo_entity_value)]

                    # THEN REGARDING MESSAGES
                    assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_ok():
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp', side_effect=_mock_pysradb):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                study_id = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = _store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])

                mock_sqs.send_message = Mock()

                input_body = json.dumps({'geo_entity_id': inserted_geo_study_id})

                # WHEN
                actual_result = E_get_study_srp.handler(_sqs_wrap([input_body]), 'a context')

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'''select sp.* from sra_project sp
                                            join geo_study_sra_project_link on id = sra_project_id
                                            where geo_study_id={inserted_geo_study_id}''')
                actual_ok_rows = database_cursor.fetchall()
                sra_project_id = actual_ok_rows[0][0]
                assert actual_ok_rows[0][1] == DEFAULT_FIXTURE['srp']

                database_cursor.execute(f'select * from sra_project_missing where geo_study_id={inserted_geo_study_id}')
                actual_ko_rows = database_cursor.fetchall()
                assert actual_ko_rows == []

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 1
                expected_calls = [call(QueueUrl=E_get_study_srp.output_sqs, MessageBody=json.dumps({'sra_project_id': sra_project_id}))]
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
                request_id = _provide_random_request_id()

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                study_id = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = _store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])

                mock_sqs.send_message = Mock()
                mock_sra_web_gse_to_srp.side_effect = pysradb_exception(pysradb_exception_info)

                input_body = json.dumps({'geo_entity_id': inserted_geo_study_id})

                # WHEN
                actual_result = E_get_study_srp.handler(_sqs_wrap([input_body]), 'a context')

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'''select srp from sra_project
                                            join geo_study_sra_project_link on id = sra_project_id
                                            where geo_study_id={inserted_geo_study_id}''')
                actual_ok_rows = database_cursor.fetchall()
                assert actual_ok_rows == []

                database_cursor.execute(
                    f'select pysradb_error_reference_id, details from sra_project_missing where geo_study_id={inserted_geo_study_id}')
                actual_ko_rows = database_cursor.fetchall()[0]
                database_cursor.execute(f"select id from pysradb_error_reference where operation='gse_to_srp' and name='{pysradb_exception_name}'")
                pysradb_error_reference_id = database_cursor.fetchone()[0]
                assert actual_ko_rows[0] == pysradb_error_reference_id
                assert re.match(rf"'?{pysradb_exception_info}'?", actual_ko_rows[1])

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_just_link_with_no_new_srp_on_new_gse_with_same_srp():
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp', side_effect=_mock_pysradb):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()
                additional_study_id = 200456456
                additional_gse = str(additional_study_id).replace('200', 'GSE', 3)

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                ncbi_study_id_1 = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                geo_study_id_1 = _store_test_geo_study(database_holder, ncbi_study_id_1, DEFAULT_FIXTURE['gse'])
                ncbi_study_id_2 = _stores_test_ncbi_study(database_holder, request_id, additional_study_id)
                geo_study_id_2 = _store_test_geo_study(database_holder, ncbi_study_id_2, additional_gse)
                sra_project_id = _store_test_sra_project(database_holder, geo_study_id_1, DEFAULT_FIXTURE['srp'])

                mock_sqs.send_message = Mock()

                input_body = json.dumps({'geo_entity_id': geo_study_id_2})

                link_rows_before, srp_rows_before = _check_link_and_srp_rows(database_holder, [ncbi_study_id_1, ncbi_study_id_2], DEFAULT_FIXTURE['srp'])
                assert link_rows_before == 1
                assert srp_rows_before == 1

                # WHEN
                actual_result = E_get_study_srp.handler(_sqs_wrap([input_body]), 'a context')

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                link_rows_after, srp_rows_after = _check_link_and_srp_rows(database_holder, [ncbi_study_id_1, ncbi_study_id_2], DEFAULT_FIXTURE['srp'])
                assert link_rows_after == 2
                assert srp_rows_after == 1

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 1
                mock_sqs.send_message.assert_called_with(
                    QueueUrl=E_get_study_srp.output_sqs,
                    MessageBody=json.dumps({'sra_project_id': sra_project_id})
                )


def test_e_get_study_srp_skip_unexpected_results():
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()
                unexpected_srp = 'DRP010911'

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                study_id = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = _store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])

                mock_sqs.send_message = Mock()
                mock_sra_web_gse_to_srp.return_value = {'study_accession': [unexpected_srp]}

                input_body = json.dumps({'geo_entity_id': inserted_geo_study_id})

                # WHEN
                actual_result = E_get_study_srp.handler(_sqs_wrap([input_body]), 'a context')

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'''select srp from sra_project
                                            join geo_study_sra_project_link on id = sra_project_id
                                            where geo_study_id={inserted_geo_study_id}''')
                actual_ok_rows = database_cursor.fetchall()
                assert actual_ok_rows == []

                database_cursor.execute(f'select * from sra_project_missing where geo_study_id={inserted_geo_study_id}')
                actual_ko_rows = database_cursor.fetchall()
                assert actual_ko_rows == []

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_f_get_study_srrs_ok():
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr', side_effect=_mock_pysradb):
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()
                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                study_id = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = _store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])
                inserted_sra_project_id = _store_test_sra_project(database_holder, inserted_geo_study_id, DEFAULT_FIXTURE['srp'])

                mock_sqs.send_message_batch = Mock()

                input_body = json.dumps({'sra_project_id': inserted_sra_project_id})

                # WHEN
                actual_result = F_get_study_srrs.handler(_sqs_wrap([input_body]), 'a context')

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f'select srr from sra_run where sra_project_id={inserted_sra_project_id}')
                actual_ok_rows = database_cursor.fetchall()
                actual_ok_rows = actual_ok_rows.sort()
                expected_rows = [(srr,) for srr in DEFAULT_FIXTURE['srrs']]
                expected_rows = expected_rows.sort()
                assert actual_ok_rows == expected_rows

                database_cursor.execute(f'select * from sra_run_missing where sra_project_id={inserted_sra_project_id}')
                actual_ko_rows = database_cursor.fetchall()
                assert actual_ko_rows == []

                # THEN REGARDING MESSAGES
                expected_calls = [f'{{"srr": "{srr}"}}' for srr in DEFAULT_FIXTURE['srrs']]

                assert mock_sqs.send_message_batch.call_count == 1

                actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs.send_message_batch.call_args_list]
                actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]

                assert expected_calls == actual_calls_message_bodies


@pytest.mark.parametrize('pysradb_exception, pysradb_exception_info, pysradb_exception_name', [
    (AttributeError, 'jander', 'ATTRIBUTE_ERROR'),
    (TypeError, 'clander', 'TYPE_ERROR')
])
def test_f_get_study_srrs_ko(pysradb_exception, pysradb_exception_info, pysradb_exception_name):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr') as mock_sra_web_srp_to_srr:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                study_id = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])
                inserted_geo_study_id = _store_test_geo_study(database_holder, study_id, DEFAULT_FIXTURE['gse'])
                inserted_sra_project_id = _store_test_sra_project(database_holder, inserted_geo_study_id, DEFAULT_FIXTURE['srp'])

                mock_sqs.send_message_batch = Mock()
                mock_sra_web_srp_to_srr.side_effect = pysradb_exception(pysradb_exception_info)

                input_body = json.dumps({'sra_project_id': inserted_sra_project_id})

                # WHEN
                actual_result = F_get_study_srrs.handler(_sqs_wrap([input_body]), 'a context')

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

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message_batch.call_count == 0

#
# def test_g_get_srr_metadata_ok():
#     with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
#         with patch.object(G_get_srr_metadata.http, 'request', side_effect=_mock_eutils):
#             with H2ConnectionManager() as database_holder:
