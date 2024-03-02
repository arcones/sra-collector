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
from utils_test import _truncate_db

sys.path.append('infra/lambdas/code')
import A_get_user_query
import B_get_query_pages
import C_get_study_ids
import D_get_study_geo
import E_get_study_srp
import F_get_study_srrs

os.environ['ENV'] = 'test'


@pytest.fixture(scope='session')
def database_holder():
    database_connection, database_cursor = _truncate_db()
    yield database_cursor, database_connection
    database_cursor.close()
    database_connection.close()


FIXTURE = {'query': 'rna seq and homo sapiens and myeloid and leukemia', 'results': 1096, 'default_study_id': 200126815, 'default_gse': 'GSE126815', 'default_srp': 'SRP185522'}


def test_a_get_user_query():
    with patch.object(A_get_user_query, 'sqs') as mock_sqs:
        # GIVEN
        request_id = _provide_random_request_id()

        ncbi_query = FIXTURE['query']

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


def test_b_get_query_pages(database_holder):
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs_send:
        with patch.object(B_get_query_pages.http, 'request') as mock_http_request:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'ncbi_query': FIXTURE['query']}).replace('"', '\"')

            mock_sqs_send.send_message_batch = Mock()
            with open('tests/fixtures/B_get_query_pages_mock_esearch.json') as response:
                mock_http_request.return_value.data = response.read()

            # WHEN
            actual_result = B_get_query_pages.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f"select id, query, geo_count from sracollector_dev.request where id='{request_id}'")
            actual_rows = database_cursor.fetchall()
            expected_row = [(request_id, FIXTURE['query'], FIXTURE['results'])]
            assert actual_rows == expected_row

            # THEN REGARDING MESSAGES
            expected_calls = [f'{{"request_id": "{request_id}", "ncbi_query": "{FIXTURE["query"]}", "retstart": 0, "retmax": 500}}',
                              f'{{"request_id": "{request_id}", "ncbi_query": "{FIXTURE["query"]}", "retstart": 500, "retmax": 500}}',
                              f'{{"request_id": "{request_id}", "ncbi_query": "{FIXTURE["query"]}", "retstart": 1000, "retmax": 500}}']

            assert mock_sqs_send.send_message_batch.call_count == 1

            actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs_send.send_message_batch.call_args_list]
            actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]
            assert expected_calls == actual_calls_message_bodies


def test_b_get_query_pages_skip_already_processed_study_id(database_holder):
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs:
        with patch.object(B_get_query_pages.http, 'request') as mock_http_request:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'ncbi_query': FIXTURE['query']}).replace('"', '\"')

            mock_sqs.send_message_batch = Mock()

            with open('tests/fixtures/B_get_query_pages_mock_esearch.json') as response:
                mock_http_request.return_value.data = response.read()

            _store_test_request(database_holder, request_id, FIXTURE['query'])

            # WHEN
            actual_result = B_get_query_pages.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f"select id from sracollector_dev.request where id='{request_id}'")
            actual_rows = database_cursor.fetchall()
            assert actual_rows == [(request_id,)]

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 0


def test_c_get_study_ids():
    with patch.object(C_get_study_ids, 'sqs') as mock_sqs:
        with patch.object(C_get_study_ids.http, 'request') as mock_http_request:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'ncbi_query': FIXTURE['query'], 'retstart': 0, 'retmax': 500}).replace('"', '\"')

            mock_sqs.send_message_batch = Mock()
            with open('tests/fixtures/C_get_study_ids_mocked_esearch.json') as response:
                mock_http_request.return_value.data = response.read()

            # WHEN
            actual_result = C_get_study_ids.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING MESSAGES
            expected_study_ids = [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391]
            expected_call = [f'{{"request_id": "{request_id}", "study_id": {expected_study_id}}}' for expected_study_id in expected_study_ids]

            assert mock_sqs.send_message_batch.call_count == 1

            actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs.send_message_batch.call_args_list]
            actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]

            assert expected_call.sort() == actual_calls_message_bodies.sort()


def test_d_get_study_geos_gse(database_holder):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request') as mock_http_request:
                # GIVEN
                request_id = _provide_random_request_id()

                mock_sqs.send_message = Mock()
                mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}
                with open('tests/fixtures/D_get_study_geo_mocked_esummary_gse.json') as response:
                    mock_http_request.return_value.data = response.read()

                input_body = json.dumps({'request_id': request_id, 'study_id': FIXTURE['default_study_id']}).replace('"', '\"')

                _store_test_request(database_holder, request_id, FIXTURE['query'])

                # WHEN
                actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                # THEN REGARDING DATA
                database_cursor, _ = database_holder
                database_cursor.execute(f"select ncbi_id, request_id, gse from sracollector_dev.geo_study where request_id='{request_id}'")
                actual_row = database_cursor.fetchall()
                assert actual_row == [(FIXTURE['default_study_id'], request_id, FIXTURE['default_gse'])]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 1
                mock_sqs.send_message.assert_called_with(
                    QueueUrl=D_get_study_geo.output_sqs,
                    MessageBody=json.dumps({'request_id': request_id, 'gse': FIXTURE['default_gse']})
                )


def test_d_get_study_geos_gsm(database_holder):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request') as mock_http_request:
                # GIVEN
                request_id = _provide_random_request_id()
                study_id = 305668979
                gsm = 'GSM5668979'

                input_body = json.dumps({'request_id': request_id, 'study_id': study_id}).replace('"', '\"')

                mock_sqs.send_message = Mock()
                mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}
                with open('tests/fixtures/D_get_study_geo_mocked_esummary_gsm.json') as response:
                    mock_http_request.return_value.data = response.read()

                _store_test_request(database_holder, request_id, FIXTURE['query'])

                # WHEN
                actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                # THEN REGARDING DATA
                database_cursor, _ = database_holder
                database_cursor.execute(f"select ncbi_id, request_id, gsm from sracollector_dev.geo_experiment where request_id='{request_id}'")
                actual_row = database_cursor.fetchall()
                assert actual_row == [(study_id, request_id, gsm)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_d_get_study_geos_gpl(database_holder):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request') as mock_http_request:
                # GIVEN
                request_id = _provide_random_request_id()
                study_id = 100019750
                gpl = 'GPL19750'

                input_body = json.dumps({'request_id': request_id, 'study_id': study_id}).replace('"', '\"')

                mock_sqs.send_message = Mock()
                mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}
                with open('tests/fixtures/D_get_study_geo_mocked_esummary_gpl.json') as response:
                    mock_http_request.return_value.data = response.read()

                _store_test_request(database_holder, request_id, FIXTURE['query'])

                # WHEN
                actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                # THEN REGARDING DATA
                database_cursor, _ = database_holder
                database_cursor.execute(f"select ncbi_id, request_id, gpl from sracollector_dev.geo_platform where request_id='{request_id}'")
                actual_row = database_cursor.fetchall()
                assert actual_row == [(study_id, request_id, gpl)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_d_get_study_geos_gds(database_holder):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request') as mock_http_request:
                # GIVEN
                request_id = _provide_random_request_id()
                study_id = 3268
                gds = 'GDS3268'

                input_body = json.dumps({'request_id': request_id, 'study_id': study_id}).replace('"', '\"')

                mock_sqs.send_message = Mock()
                mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}
                with open('tests/fixtures/D_get_study_geo_mocked_esummary_gds.json') as response:
                    mock_http_request.return_value.data = response.read()

                _store_test_request(database_holder, request_id, FIXTURE['query'])

                # WHEN
                actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                # THEN REGARDING DATA
                database_cursor, _ = database_holder
                database_cursor.execute(f"select ncbi_id, request_id, gds from sracollector_dev.geo_data_set where request_id='{request_id}'")
                actual_row = database_cursor.fetchall()
                assert actual_row == [(study_id, request_id, gds)]

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_d_get_study_geos_skip_already_processed_study_id(database_holder):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs:
        with patch.object(D_get_study_geo.secrets, 'get_secret_value') as mock_secrets_get_secret_value:
            with patch.object(D_get_study_geo.http, 'request') as mock_http_request:
                # GIVEN
                request_id = _provide_random_request_id()

                input_body = json.dumps({'request_id': request_id, 'study_id': FIXTURE['default_study_id']}).replace('"', '\"')

                mock_sqs.send_message = Mock()
                mock_secrets_get_secret_value.return_value = {'SecretString': '{"value":"mockedSecret"}'}
                with open('tests/fixtures/D_get_study_geo_mocked_esummary_gse.json') as response:
                    mock_http_request.return_value.data = response.read()

                _store_test_request(database_holder, request_id, FIXTURE['query'])
                _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])

                # WHEN
                actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs([input_body]), 'a context')

                # THEN REGARDING DATA
                database_cursor, _ = database_holder
                database_cursor.execute(f"select ncbi_id, request_id, gse from sracollector_dev.geo_study where request_id='{request_id}'")
                actual_rows = database_cursor.fetchall()
                expected_rows = [(FIXTURE['default_study_id'], request_id, FIXTURE['default_gse'])]

                assert actual_rows == expected_rows

                # THEN REGARDING MESSAGES
                assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_ok(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'gse': FIXTURE['default_gse']})

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.return_value = {'study_accession': [FIXTURE['default_srp']]}

            _store_test_request(database_holder, request_id, FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            expected_ok_rows = [(FIXTURE['default_srp'],)]
            assert actual_ok_rows == expected_ok_rows

            database_cursor.execute(f'select * from sracollector_dev.sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()
            assert actual_ko_rows == []

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 1

            expected_calls = [call(QueueUrl=E_get_study_srp.output_sqs, MessageBody=json.dumps({'request_id': request_id, 'srp': FIXTURE['default_srp']}))]

            actual_calls = mock_sqs.send_message.call_args_list

            assert expected_calls == actual_calls


def test_e_get_study_srp_attribute_error(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'gse': FIXTURE['default_gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.side_effect = AttributeError('jander')

            _store_test_request(database_holder, request_id, FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(
                f'select pysradb_error_reference_id, details from sracollector_dev.sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()[0]
            database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='gse_to_srp' and name='ATTRIBUTE_ERROR'")
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

            input_body = json.dumps({'request_id': request_id, 'gse': FIXTURE['default_gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.side_effect = ValueError('clander')

            _store_test_request(database_holder, request_id, FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(
                f'select pysradb_error_reference_id, details from sracollector_dev.sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()[0]
            database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='gse_to_srp' and name='VALUE_ERROR'")
            pysradb_error_reference_id = database_cursor.fetchone()[0]
            assert actual_ko_rows == (pysradb_error_reference_id, 'clander')

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == 0


def test_e_get_study_srp_key_error(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            request_id = _provide_random_request_id()

            input_body = json.dumps({'request_id': request_id, 'gse': FIXTURE['default_gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.side_effect = KeyError('crispin')

            _store_test_request(database_holder, request_id, FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(
                f'select pysradb_error_reference_id, details from sracollector_dev.sra_project_missing where geo_study_id={inserted_geo_study_id}')
            actual_ko_rows = database_cursor.fetchall()[0]
            database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='gse_to_srp' and name='KEY_ERROR'")
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

        _store_test_request(database_holder, request_id, FIXTURE['query'])
        inserted_geo_study_id_1 = _store_test_geo_study(database_holder, request_id, study_ids[0], gses[0])
        inserted_sra_project_id = _store_test_sra_project(database_holder, srp, inserted_geo_study_id_1)
        _store_test_geo_study(database_holder, request_id, study_ids[1], gses[1])
        gses_for_sql_in = ', '.join([f"'{gse}'" for gse in gses])

        database_cursor, _ = database_holder
        database_cursor.execute(f'''select count(*) from sracollector_dev.geo_study_sra_project_link
                                    join sracollector_dev.geo_study on geo_study_sra_project_link.geo_study_id = geo_study.id
                                    where gse in ({gses_for_sql_in})''')
        link_rows_before = database_cursor.fetchone()[0]
        assert link_rows_before == 1
        database_cursor.execute(f'select count(*) from sracollector_dev.sra_project where id={inserted_sra_project_id}')
        srp_rows_before = database_cursor.fetchone()[0]
        assert srp_rows_before == 1

        input_body = json.dumps({'request_id': request_id, 'gse': gses[1]})

        # WHEN
        actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor.execute(f'''select count(*) from sracollector_dev.geo_study_sra_project_link
                                            join sracollector_dev.geo_study on geo_study_sra_project_link.geo_study_id = geo_study.id
                                            where gse in ({gses_for_sql_in})''')
        link_rows_after = database_cursor.fetchone()[0]
        assert link_rows_after == 2
        database_cursor.execute(f'select count(*) from sracollector_dev.sra_project where id={inserted_sra_project_id}')
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

        input_body = json.dumps({'request_id': request_id, 'gse': FIXTURE['default_gse']}).replace('"', '\"')

        mock_sqs.send_message = Mock()

        _store_test_request(database_holder, request_id, FIXTURE['query'])
        inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])
        inserted_sra_project_id = _store_test_sra_project(database_holder, FIXTURE['default_srp'], inserted_geo_study_id)

        # WHEN
        actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f'select srp from sracollector_dev.sra_project where id={inserted_sra_project_id}')
        actual_ok_rows = database_cursor.fetchall()
        assert actual_ok_rows == [(FIXTURE['default_srp'],)]

        database_cursor.execute(f'select pysradb_error_reference_id from sracollector_dev.sra_project_missing where geo_study_id={inserted_geo_study_id}')
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

            input_body = json.dumps({'request_id': request_id, 'gse': FIXTURE['default_gse']}).replace('"', '\"')

            mock_sqs.send_message = Mock()
            mock_sra_web_gse_to_srp.return_value = {'study_accession': [unexpected_srp]}

            _store_test_request(database_holder, request_id, FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id={inserted_geo_study_id}''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(f'select * from sracollector_dev.sra_project_missing where geo_study_id={inserted_geo_study_id}')
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

            input_body = json.dumps({'request_id': request_id, 'srp': FIXTURE['default_srp']}).replace('"', '\"')

            _store_test_request(database_holder, request_id, FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])
            inserted_sra_project_id = _store_test_sra_project(database_holder, FIXTURE['default_srp'], inserted_geo_study_id)

            # WHEN
            actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id={inserted_sra_project_id}')
            actual_ok_rows = database_cursor.fetchall()
            actual_ok_rows = actual_ok_rows.sort()
            expected_rows = [(srr,) for srr in srrs]
            expected_rows = expected_rows.sort()
            assert actual_ok_rows == expected_rows

            database_cursor.execute(f'select * from sracollector_dev.sra_run_missing where sra_project_id={inserted_sra_project_id}')
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

            input_body = json.dumps({'request_id': request_id, 'srp': FIXTURE['default_srp']}).replace('"', '\"')

            mock_sqs.send_message_batch = Mock()
            mock_sra_web_srp_to_srr.side_effect = AttributeError("'NoneType' object has no attribute 'columns'")

            _store_test_request(database_holder, request_id, FIXTURE['query'])
            inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])
            inserted_sra_project_id = _store_test_sra_project(database_holder, FIXTURE['default_srp'], inserted_geo_study_id)

            # WHEN
            actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs([input_body]), 'a context')

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id={inserted_sra_project_id}')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(f'select pysradb_error_reference_id, details from sracollector_dev.sra_run_missing where sra_project_id={inserted_sra_project_id}')
            actual_ko_rows = database_cursor.fetchall()
            database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='srp_to_srr' and name='ATTRIBUTE_ERROR'")
            pysradb_error_reference_id = database_cursor.fetchone()[0]
            assert actual_ko_rows == [(pysradb_error_reference_id, "'NoneType' object has no attribute 'columns'")]

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message_batch.call_count == 0


def test_f_get_study_srrs_skip_already_processed_srp(database_holder):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs:
        # GIVEN
        request_id = _provide_random_request_id()
        srr = 'SRR787899'

        input_body = json.dumps({'request_id': request_id, 'srp': FIXTURE['default_srp']})

        mock_sqs.send_message_batch = Mock()

        _store_test_request(database_holder, request_id, FIXTURE['query'])
        geo_study_id = _store_test_geo_study(database_holder, request_id, FIXTURE['default_study_id'], FIXTURE['default_gse'])
        sra_project_id = _store_test_sra_project(database_holder, FIXTURE['default_srp'], geo_study_id)
        _store_test_sra_run(database_holder, srr, sra_project_id)

        # WHEN
        actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs([input_body]), 'a context')

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id={sra_project_id}')
        actual_ok_rows = database_cursor.fetchall()
        assert actual_ok_rows == [(srr,)]

        database_cursor.execute(f'select pysradb_error_reference_id, details from sracollector_dev.sra_run_missing where sra_project_id={sra_project_id}')
        actual_ko_rows = database_cursor.fetchall()
        assert actual_ko_rows == []

        # THEN REGARDING MESSAGES
        assert mock_sqs.send_message_batch.call_count == 0
