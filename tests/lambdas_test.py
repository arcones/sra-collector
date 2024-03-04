import json
import os
import sys
from unittest.mock import call
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from utils_test import _get_customized_input_from_sqs
from utils_test import _provide_random_request_id
from utils_test import _store_test_geo_study
from utils_test import _store_test_request
from utils_test import _store_test_sra_project
from utils_test import _store_test_sra_run
from utils_test import _stores_test_ncbi_study
from utils_test import H2ConnectionManager

sys.path.append('infra/lambdas/code')
import A_get_user_query
import B_get_query_pages
import C_get_study_ids
import D_get_study_geo
import E_get_study_srp
import F_get_study_srrs

os.environ['ENV'] = 'test'

DEFAULT_FIXTURE = {'query': 'rna seq and homo sapiens and myeloid and leukemia', 'results': 1096, 'ncbi_id': 200126815, 'gse': 'GSE126815', 'srp': 'SRP185522'}


def test_a_get_user_query():
    with patch.object(A_get_user_query, 'sqs') as mock_sqs:
        # GIVEN
        request_id = _provide_random_request_id()

        ncbi_query = DEFAULT_FIXTURE['query']

        input_body = json.dumps({'ncbi_query': ncbi_query}).replace('"', '\"')

        mock_sqs.send_message = Mock()

        with open(f'tests/fixtures/A_get_user_query_input.json') as json_data:
            payload = json.load(json_data)
            payload['requestContext']['requestId'] = request_id
            payload['body'] = input_body

        # WHEN
        actual_result = A_get_user_query.handler(payload, 'a context')

        # THEN REGARDING LAMBDA
        assert actual_result['statusCode'] == 201
        assert actual_result['body'] == f'{{"request_id": "{request_id}", "ncbi_query": "{ncbi_query}"}}'

        # THEN REGARDING MESSAGES
        assert mock_sqs.send_message.call_count == 1
        mock_sqs.send_message.assert_called_with(QueueUrl=A_get_user_query.output_sqs, MessageBody=json.dumps({'request_id': request_id, 'ncbi_query': ncbi_query}))


def test_b_get_query_pages():
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs_send:
        with patch.object(B_get_query_pages.http, 'request') as mock_http_request:
            with H2ConnectionManager() as (database_connection, database_cursor):
                # GIVEN
                request_id = _provide_random_request_id()

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query']}).replace('"', '\"')

                mock_sqs_send.send_message_batch = Mock()
                with open('tests/fixtures/B_get_query_pages_mock_esearch.json') as response:
                    mock_http_request.return_value.data = response.read()

                # WHEN
                actual_result = B_get_query_pages.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}

                # THEN REGARDING DATA
                database_cursor.execute(f"select id, query, geo_count from request where id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                expected_row = [(request_id, DEFAULT_FIXTURE['query'], DEFAULT_FIXTURE['results'])]
                assert actual_rows == expected_row

                # THEN REGARDING MESSAGES
                expected_calls = [f'{{"request_id": "{request_id}", "ncbi_query": "{DEFAULT_FIXTURE["query"]}", "retstart": 0, "retmax": 500}}',
                                  f'{{"request_id": "{request_id}", "ncbi_query": "{DEFAULT_FIXTURE["query"]}", "retstart": 500, "retmax": 500}}',
                                  f'{{"request_id": "{request_id}", "ncbi_query": "{DEFAULT_FIXTURE["query"]}", "retstart": 1000, "retmax": 500}}']

                assert mock_sqs_send.send_message_batch.call_count == 1

                actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs_send.send_message_batch.call_args_list]
                actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]
                assert expected_calls == actual_calls_message_bodies


def test_b_get_query_pages_skip_already_processed_study_id():
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs:
        with patch.object(B_get_query_pages.http, 'request') as mock_http_request:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query']}).replace('"', '\"')

                mock_sqs.send_message_batch = Mock()

                with open('tests/fixtures/B_get_query_pages_mock_esearch.json') as response:
                    mock_http_request.return_value.data = response.read()

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])

                # WHEN
                actual_result = B_get_query_pages.handler(_get_customized_input_from_sqs([input_body]), 'a context')

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
        with patch.object(C_get_study_ids.http, 'request') as mock_http_request:
            with H2ConnectionManager() as database_holder:
                # GIVEN
                request_id = _provide_random_request_id()

                input_body = json.dumps({'request_id': request_id, 'ncbi_query': DEFAULT_FIXTURE['query'], 'retstart': 0, 'retmax': 500}).replace('"', '\"')

                mock_sqs.send_message_batch = Mock()
                with open('tests/fixtures/C_get_study_ids_mocked_esearch.json') as response:
                    mock_http_request.return_value.data = response.read()

                _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])

                # WHEN
                actual_result = C_get_study_ids.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                # THEN REGARDING LAMBDA
                assert actual_result == {'batchItemFailures': []}  ## TODO hay test en los que no se hace ninguna aseveración con esta

                # THEN REGARDING DATA
                _, database_cursor = database_holder
                database_cursor.execute(f"select ncbi_id, request_id from ncbi_study where request_id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                expected_study_ids = [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391]
                assert actual_rows == [(study_id, request_id) for study_id in expected_study_ids]

                # THEN REGARDING MESSAGES
                expected_call = [f'{{"request_id": "{request_id}", "study_id": {expected_study_id}}}' for expected_study_id in expected_study_ids]

                assert mock_sqs.send_message_batch.call_count == 1

                actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs.send_message_batch.call_args_list]
                actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]

                assert expected_call.sort() == actual_calls_message_bodies.sort()


def test_d_get_study_geos_gse():
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request') as mock_http_request:
                with H2ConnectionManager() as database_holder:
                    # GIVEN
                    request_id = _provide_random_request_id()

                    input_body = json.dumps({'request_id': request_id, 'study_id': DEFAULT_FIXTURE['ncbi_id']}).replace('"', '\"')

                    mock_sqs.send_message = Mock()
                    mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}
                    with open('tests/fixtures/D_get_study_geo_mocked_esummary_gse.json') as response:
                        mock_http_request.return_value.data = response.read()

                    _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                    study_id = _stores_test_ncbi_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'])

                    # WHEN
                    actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                    # THEN REGARDING DATA
                    _, database_cursor = database_holder
                    database_cursor.execute(f"select ncbi_study_id, gse from geo_study where ncbi_study_id='{study_id}'")
                    actual_row = database_cursor.fetchall()
                    assert actual_row == [(study_id, DEFAULT_FIXTURE['gse'])]

                    # THEN REGARDING MESSAGES
                    assert mock_sqs.send_message.call_count == 1
                    mock_sqs.send_message.assert_called_with(
                        QueueUrl=D_get_study_geo.output_sqs,
                        MessageBody=json.dumps({'request_id': request_id, 'gse': DEFAULT_FIXTURE['gse']})
                    )


@pytest.mark.parametrize('study_id, geo_table, geo_entity_name, geo_entity_value, geo_fixture', [
    (305668979, 'geo_experiment', 'gsm', 'GSM5668979', 'D_get_study_geo_mocked_esummary_gsm.json'),
    (100019750, 'geo_platform', 'gpl', 'GPL19750', 'D_get_study_geo_mocked_esummary_gpl.json'),
    (3268, 'geo_data_set', 'gds', 'GDS3268', 'D_get_study_geo_mocked_esummary_gds.json'),
])
def test_d_get_study_geos_not_gse(study_id, geo_table, geo_entity_name, geo_entity_value, geo_fixture):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request') as mock_http_request:
                with H2ConnectionManager() as database_holder:
                    # GIVEN
                    request_id = _provide_random_request_id()

                    input_body = json.dumps({'request_id': request_id, 'study_id': study_id}).replace('"', '\"')

                    mock_sqs.send_message = Mock()
                    mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}
                    with open(f'tests/fixtures/{geo_fixture}') as response:
                        mock_http_request.return_value.data = response.read()

                    _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
                    study_id = _stores_test_ncbi_study(database_holder, request_id, study_id)

                    # WHEN
                    actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                    # THEN REGARDING DATA
                    _, database_cursor = database_holder
                    database_cursor.execute(f"select ncbi_study_id, {geo_entity_name} from {geo_table} where ncbi_study_id='{study_id}'")
                    actual_row = database_cursor.fetchall()
                    assert actual_row == [(study_id, geo_entity_value)]

                    # THEN REGARDING MESSAGES
                    assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_ok(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'gse': DEFAULT_FIXTURE['gse']})

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.return_value = {'study_accession': [DEFAULT_FIXTURE['srp']]}

            _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sra_project
                                        join geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            expected_ok_rows = [(DEFAULT_FIXTURE['srp'],)]
            assert actual_ok_rows == expected_ok_rows

            database_cursor.execute(f'select * from sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()
            assert actual_ko_rows == []

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 1

            expected_calls = [call(QueueUrl=E_get_study_srp.output_sqs, MessageBody=json.dumps({'request_id': request_id, 'srp': DEFAULT_FIXTURE['srp']}))]

            actual_calls = mock_sqs.send_message.call_args_list

            assert expected_calls == actual_calls


def test_e_get_study_srp_attribute_error(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'gse': DEFAULT_FIXTURE['gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.side_effect = AttributeError('jander')

            _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sra_project
                                        join geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(
                f'select pysradb_error_reference_id, details from sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()[0]
            database_cursor.execute(f"select id from pysradb_error_reference where operation='gse_to_srp' and name='ATTRIBUTE_ERROR'")
            pysradb_error_reference_id = database_cursor.fetchone()[0]
            assert actual_ko_rows == (pysradb_error_reference_id, 'jander')

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_value_error(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()
            # gse = 'GSE110021'

            input_body = json.dumps({'request_id': request_id, 'gse': DEFAULT_FIXTURE['gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.side_effect = ValueError('clander')

            _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sra_project
                                        join geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(
                f'select pysradb_error_reference_id, details from sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()[0]
            database_cursor.execute(f"select id from pysradb_error_reference where operation='gse_to_srp' and name='VALUE_ERROR'")
            pysradb_error_reference_id = database_cursor.fetchone()[0]
            assert actual_ko_rows == (pysradb_error_reference_id, 'clander')

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_key_error(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'gse': DEFAULT_FIXTURE['gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.side_effect = KeyError('crispin')

            _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sra_project
                                        join geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(
                f'select pysradb_error_reference_id, details from sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()[0]
            database_cursor.execute(f"select id from pysradb_error_reference where operation='gse_to_srp' and name='KEY_ERROR'")
            pysradb_error_reference_id = database_cursor.fetchone()[0]
            assert actual_ko_rows == (pysradb_error_reference_id, "'crispin'")

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_skip_already_linked_gse(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        # GIVEN
        mock_sqs.send_message = Mock()

        request_id = _provide_random_request_id()
        study_ids = [20094225, 20094169]
        gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
        srp = 'SRP094854'

        _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
        inserted_geo_study_id_1 = _store_test_geo_study(database_holder, request_id, study_ids[0], gses[0])
        inserted_sra_project_id = _store_test_sra_project(database_holder, srp, inserted_geo_study_id_1)
        _store_test_geo_study(database_holder, request_id, study_ids[1], gses[1])
        gses_for_sql_in = ', '.join([f"'{gse}'" for gse in gses])

        database_cursor, _ = database_holder
        database_cursor.execute(f'''select count(*) from geo_study_sra_project_link
                                    join geo_study on geo_study_sra_project_link.geo_study_id = geo_study.id
                                    where gse in ({gses_for_sql_in})''')
        link_rows_before = database_cursor.fetchone()[0]
        assert link_rows_before == 1
        database_cursor.execute(f'select count(*) from sra_project where id={inserted_sra_project_id}')
        srp_rows_before = database_cursor.fetchone()[0]
        assert srp_rows_before == 1

        input_body = json.dumps({'request_id': request_id, 'gse': gses[1]})

        # WHEN
        actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor.execute(f'''select count(*) from geo_study_sra_project_link
                                            join geo_study on geo_study_sra_project_link.geo_study_id = geo_study.id
                                            where gse in ({gses_for_sql_in})''')
        link_rows_after = database_cursor.fetchone()[0]
        assert link_rows_after == 2
        database_cursor.execute(f'select count(*) from sra_project where id={inserted_sra_project_id}')
        srp_rows_after = database_cursor.fetchone()[0]
        assert srp_rows_after == 1

        # THEN REGARDING MESSAGES
        assert mock_sqs.send_message.call_count == 1
        mock_sqs.send_message.assert_called_with(
            QueueUrl=E_get_study_srp.output_sqs,
            MessageBody=json.dumps({'request_id': request_id, 'srp': srp})
        )


def test_e_get_study_srp_skip_already_processed_geo(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        # GIVEN
        request_id = _provide_random_request_id()

        input_body = json.dumps({'request_id': request_id, 'gse': DEFAULT_FIXTURE['gse']}).replace('"', '\"')

        mock_sqs.send_message = Mock()

        _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
        inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])
        inserted_sra_project_id = _store_test_sra_project(database_holder, DEFAULT_FIXTURE['srp'], inserted_geo_study_id)

        # WHEN
        actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f'select srp from sra_project where id={inserted_sra_project_id}')
        actual_ok_rows = database_cursor.fetchall()
        assert actual_ok_rows == [(DEFAULT_FIXTURE['srp'],)]

        database_cursor.execute(f'select pysradb_error_reference_id from sra_project_missing where geo_study_id={inserted_geo_study_id}')
        actual_ko_rows = database_cursor.fetchall()
        assert actual_ko_rows == []

        # THEN REGARDING MESSAGES
        assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_skip_unexpected_results(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()
            unexpected_srp = 'DRP010911'

            input_body = json.dumps({'request_id': request_id, 'gse': DEFAULT_FIXTURE['gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.return_value = {'study_accession': [unexpected_srp]}

            _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
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


def test_f_get_study_srrs_ok(database_holder):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr') as mock_sra_web_srp_to_srr:
            # GIVEN
            request_id = _provide_random_request_id()
            srrs = ['SRR22873806', 'SRR22873807']

            mock_sqs.send_message_batch = Mock()
            mock_sra_web_srp_to_srr.return_value = {'run_accession': srrs}

            input_body = json.dumps({'request_id': request_id, 'srp': DEFAULT_FIXTURE['srp']}).replace('"', '\"')

            _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])
            inserted_sra_project_id = _store_test_sra_project(database_holder, DEFAULT_FIXTURE['srp'], inserted_geo_study_id)

            # WHEN
            actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'select srr from sra_run where sra_project_id={inserted_sra_project_id}')
            actual_ok_rows = database_cursor.fetchall()
            actual_ok_rows = actual_ok_rows.sort()
            expected_rows = [(srr,) for srr in srrs]
            expected_rows = expected_rows.sort()
            assert actual_ok_rows == expected_rows

            database_cursor.execute(f'select * from sra_run_missing where sra_project_id={inserted_sra_project_id}')
            actual_ko_rows = database_cursor.fetchall()
            assert actual_ko_rows == []

            # THEN REGARDING MESSAGES
            expected_calls = [f'{{"request_id": "{request_id}", "srr": "{srr}"}}' for srr in srrs]

            assert mock_sqs.send_message_batch.call_count == 1

            actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs.send_message_batch.call_args_list]
            actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]

            assert expected_calls.sort() == actual_calls_message_bodies.sort()


def test_f_get_study_srrs_ko(database_holder):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr') as mock_sra_web_srp_to_srr:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'srp': DEFAULT_FIXTURE['srp']}).replace('"', '\"')

            mock_sqs.send_message_batch = Mock()
            mock_sra_web_srp_to_srr.side_effect = AttributeError("'NoneType' object has no attribute 'columns'")

            _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])
            inserted_sra_project_id = _store_test_sra_project(database_holder, DEFAULT_FIXTURE['srp'], inserted_geo_study_id)

            # WHEN
            actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'select srr from sra_run where sra_project_id={inserted_sra_project_id}')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(f'select pysradb_error_reference_id, details from sra_run_missing where sra_project_id={inserted_sra_project_id}')
            actual_ko_rows = database_cursor.fetchall()
            database_cursor.execute(f"select id from pysradb_error_reference where operation='srp_to_srr' and name='ATTRIBUTE_ERROR'")
            pysradb_error_reference_id = database_cursor.fetchone()[0]
            assert actual_ko_rows == [(pysradb_error_reference_id, "'NoneType' object has no attribute 'columns'")]

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message_batch.call_count == 0


def test_f_get_study_srrs_skip_already_processed_srp(database_holder):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        # GIVEN
        request_id = _provide_random_request_id()
        srr = 'SRR787899'

        input_body = json.dumps({'request_id': request_id, 'srp': DEFAULT_FIXTURE['srp']})

        mock_sqs.send_message_batch = Mock()

        _store_test_request(database_holder, request_id, DEFAULT_FIXTURE['query'])
        geo_study_id = _store_test_geo_study(database_holder, request_id, DEFAULT_FIXTURE['ncbi_id'], DEFAULT_FIXTURE['gse'])
        sra_project_id = _store_test_sra_project(database_holder, DEFAULT_FIXTURE['srp'], geo_study_id)
        _store_test_sra_run(database_holder, srr, sra_project_id)

        # WHEN
        actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs([input_body]), 'a context')

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f'select srr from sra_run where sra_project_id={sra_project_id}')
        actual_ok_rows = database_cursor.fetchall()
        assert actual_ok_rows == [(srr,)]

        database_cursor.execute(f'select pysradb_error_reference_id, details from sra_run_missing where sra_project_id={sra_project_id}')
        actual_ko_rows = database_cursor.fetchall()
        assert actual_ko_rows == []

        # THEN REGARDING MESSAGES
        assert mock_sqs.send_message_batch.call_count == 0
