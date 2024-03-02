import json
import os
import sys
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from utils_test import _get_customized_input_from_sqs
from utils_test import _get_needed_batches_of_ten_messages
from utils_test import _provide_random_request_id
from utils_test import _store_test_geo_data_set
from utils_test import _store_test_geo_experiment
from utils_test import _store_test_geo_platform
from utils_test import _store_test_geo_study
from utils_test import _store_test_request
from utils_test import _store_test_sra_project
from utils_test import _store_test_sra_run
from utils_test import _truncate_db
from utils_test import Context

sys.path.append('infra/lambdas/code')
import A_get_user_query, B_get_query_pages, C_get_study_ids, D_get_study_geo, E_get_study_srp, F_get_study_srrs

os.environ['ENV'] = 'test'

_S_QUERY = {'query': 'stroke AND single cell rna seq AND musculus', 'results': 8}
_2XL_QUERY = {'query': 'rna seq and homo sapiens and myeloid and leukemia', 'results': 1096}


@pytest.fixture(scope='session')
def database_holder():
    database_connection, database_cursor = _truncate_db()
    yield database_cursor, database_connection
    database_cursor.close()
    database_connection.close()


def test_a_get_user_query():
    with patch.object(A_get_user_query, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message = Mock()
        function_name = 'A_get_user_query'

        request_id = _provide_random_request_id()
        ncbi_query = _S_QUERY['query']
        input_body = json.dumps({'ncbi_query': ncbi_query}).replace('"', '\"')

        with open(f'tests/fixtures/{function_name}_input.json') as json_data:
            payload = json.load(json_data)
            payload['requestContext']['requestId'] = request_id
            payload['body'] = input_body

        # WHEN
        actual_result = A_get_user_query.handler(payload, Context(function_name))

        # THEN REGARDING LAMBDA
        assert actual_result['statusCode'] == 201
        assert actual_result['body'] == f'{{"request_id": "{request_id}", "ncbi_query": "{ncbi_query}"}}'

        # THEN REGARDING MESSAGES
        assert mock_sqs_send_message.send_message.call_count == 1
        mock_sqs_send_message.send_message.assert_called_with(QueueUrl=A_get_user_query.output_sqs, MessageBody=json.dumps({'request_id': request_id, 'ncbi_query': ncbi_query}))


def test_b_get_query_pages(database_holder):
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message_batch = Mock()
        function_name = 'B_get_query_pages'

        request_id_1 = _provide_random_request_id()
        request_id_2 = _provide_random_request_id()
        input_bodies = [
            json.dumps({'request_id': request_id_1, 'ncbi_query': _S_QUERY['query']}).replace('"', '\"'),
            json.dumps({'request_id': request_id_2, 'ncbi_query': _2XL_QUERY['query']}).replace('"', '\"'),
        ]

        # WHEN
        actual_result = B_get_query_pages.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor, _ = database_holder

        database_cursor.execute(f"select id, query, geo_count from sracollector_dev.request where id in ('{request_id_1}', '{request_id_2}')")
        actual_rows = database_cursor.fetchall()
        actual_rows = sorted(actual_rows, key=lambda row: (row[0]))

        expected_rows = [
            (request_id_1, _S_QUERY['query'], _S_QUERY['results']),
            (request_id_2, _2XL_QUERY['query'], _2XL_QUERY['results'])
        ]
        expected_rows = sorted(expected_rows, key=lambda row: (row[0]))

        assert actual_rows == expected_rows

        # THEN REGARDING MESSAGES
        expected_calls = [f'{{"request_id": "{request_id_1}", "ncbi_query": "{_S_QUERY["query"]}", "retstart": 0, "retmax": 500}}',
                          f'{{"request_id": "{request_id_2}", "ncbi_query": "{_2XL_QUERY["query"]}", "retstart": 0, "retmax": 500}}',
                          f'{{"request_id": "{request_id_2}", "ncbi_query": "{_2XL_QUERY["query"]}", "retstart": 500, "retmax": 500}}',
                          f'{{"request_id": "{request_id_2}", "ncbi_query": "{_2XL_QUERY["query"]}", "retstart": 1000, "retmax": 500}}']

        assert mock_sqs_send_message.send_message_batch.call_count == 2

        actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs_send_message.send_message_batch.call_args_list]
        actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]
        assert expected_calls == actual_calls_message_bodies


def test_b_get_query_pages_skip_already_processed_study_id(database_holder):
    with patch.object(B_get_query_pages, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message_batch = Mock()
        function_name = 'B_get_query_pages'

        request_id = _provide_random_request_id()
        input_body = json.dumps({'request_id': request_id, 'ncbi_query': _S_QUERY['query']}).replace('"', '\"')

        _store_test_request(database_holder, request_id, _S_QUERY['query'])

        # WHEN
        actual_result = B_get_query_pages.handler(_get_customized_input_from_sqs([input_body]), Context(function_name))

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f"select id from sracollector_dev.request where id='{request_id}'")
        actual_rows = database_cursor.fetchall()
        assert actual_rows == [(request_id,)]

        # THEN REGARDING MESSAGES
        assert mock_sqs_send_message.send_message.call_count == 0


def test_c_get_study_ids():
    with patch.object(C_get_study_ids, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message_batch = Mock()
        function_name = 'C_get_study_ids'

        request_id_1 = _provide_random_request_id()
        request_id_2 = _provide_random_request_id()
        input_bodies = [
            json.dumps({'request_id': request_id_1, 'ncbi_query': _S_QUERY['query'], 'retstart': 0, 'retmax': 500}).replace('"', '\"'),
            json.dumps({'request_id': request_id_2, 'ncbi_query': _S_QUERY['query'], 'retstart': 0, 'retmax': 500}).replace('"', '\"'),
        ]

        # WHEN
        actual_result = C_get_study_ids.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING MESSAGES
        expected_study_ids = [200126815, 200150644, 200167593, 200174574, 200189432, 200207275, 200247102, 200247391]
        expected_calls = \
            [f'{{"request_id": "{request_id_1}", "study_id": {expected_study_id}}}' for expected_study_id in expected_study_ids] + \
            [f'{{"request_id": "{request_id_2}", "study_id": {expected_study_id}}}' for expected_study_id in expected_study_ids]

        assert mock_sqs_send_message.send_message_batch.call_count == 2

        actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs_send_message.send_message_batch.call_args_list]
        actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]

        assert expected_calls.sort() == actual_calls_message_bodies.sort()


def test_d_get_study_geos(database_holder):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message = Mock()
        function_name = 'D_get_study_geo'

        request_id = _provide_random_request_id()
        study_ids = [200126815, 305668979, 100019750, 3268]
        geos = ['GSE126815', 'GSM5668979', 'GPL19750', 'GDS3268']
        study_ids_and_geos = zip(study_ids, geos)

        input_bodies = [
            json.dumps({'request_id': request_id, 'study_id': study_id}).replace('"', '\"')
            for study_id in study_ids
        ]

        _store_test_request(database_holder, request_id, _S_QUERY['query'])

        # WHEN
        actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f"""
                                select ncbi_id, request_id, gse from sracollector_dev.geo_study where request_id='{request_id}'
                                union
                                select ncbi_id, request_id, gsm from sracollector_dev.geo_experiment where request_id='{request_id}'
                                union
                                select ncbi_id, request_id, gpl from sracollector_dev.geo_platform where request_id='{request_id}'
                                union
                                select ncbi_id, request_id, gds from sracollector_dev.geo_data_set where request_id='{request_id}'
                                """)
        actual_rows = database_cursor.fetchall()
        actual_rows = sorted(actual_rows, key=lambda row: (row[0]))

        expected_rows = [(study_id_and_geos[0], request_id, study_id_and_geos[1]) for study_id_and_geos in study_ids_and_geos]
        expected_rows = sorted(expected_rows, key=lambda row: (row[0]))

        assert actual_rows == expected_rows

        # THEN REGARDING MESSAGES
        assert mock_sqs_send_message.send_message.call_count == 1
        mock_sqs_send_message.send_message.assert_called_with(
            QueueUrl=D_get_study_geo.output_sqs,
            MessageBody=json.dumps({'request_id': request_id, 'gse': 'GSE126815'})
        )


def test_d_get_study_geos_skip_already_processed_study_id(database_holder):
    with patch.object(D_get_study_geo, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message = Mock()
        function_name = 'D_get_study_geo'

        request_id = _provide_random_request_id()
        study_ids = [200126815, 305668979, 100019750, 3268]
        geos = ['GSE126815', 'GSM5668979', 'GPL19750', 'GDS3268']
        study_ids_and_geos = zip(study_ids, geos)

        input_bodies = [
            json.dumps({'request_id': request_id, 'study_id': study_id}).replace('"', '\"')
            for study_id in study_ids
        ]

        _store_test_request(database_holder, request_id, _S_QUERY['query'])

        _store_test_geo_study(database_holder, request_id, 200126815, 'GSE126815')
        _store_test_geo_experiment(database_holder, request_id, 305668979, 'GSM5668979')
        _store_test_geo_platform(database_holder, request_id, 100019750, 'GPL19750')
        _store_test_geo_data_set(database_holder, request_id, 3268, 'GDS3268')

        # WHEN
        actual_result = D_get_study_geo.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f"""
                                select ncbi_id, request_id, gse from sracollector_dev.geo_study where request_id='{request_id}'
                                union
                                select ncbi_id, request_id, gsm from sracollector_dev.geo_experiment where request_id='{request_id}'
                                union
                                select ncbi_id, request_id, gpl from sracollector_dev.geo_platform where request_id='{request_id}'
                                union
                                select ncbi_id, request_id, gds from sracollector_dev.geo_data_set where request_id='{request_id}'
                                """)
        actual_rows = database_cursor.fetchall()
        actual_rows = sorted(actual_rows, key=lambda row: (row[0]))

        expected_rows = [(study_id_and_geos[0], request_id, study_id_and_geos[1]) for study_id_and_geos in study_ids_and_geos]
        expected_rows = sorted(expected_rows, key=lambda row: (row[0]))

        assert actual_rows == expected_rows

        # THEN REGARDING MESSAGES
        assert mock_sqs_send_message.send_message.call_count == 0


def test_e_get_study_srp_ok(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs: #TODO cambiar todas estas
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            mock_sqs.send_message = Mock()

            request_id = _provide_random_request_id()
            study_ids = [200126815, 200150644, 200167593]
            gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
            srps = ['SRP185522', 'SRP261818', 'SRP308347']

            def multiple_return_values(parameter):
                srp_results = [{'study_accession': [srp]} for srp in srps]
                gse_to_srp_mapping = dict(zip(gses, srp_results))
                return gse_to_srp_mapping.get(parameter, 'default_return_value')

            mock_sra_web_gse_to_srp.side_effect = multiple_return_values

            function_name = 'E_get_study_srp'

            study_ids_and_geos = list(zip(study_ids, gses))

            input_bodies = [
                json.dumps({'request_id': request_id, 'gse': study_id_and_gse[1]})
                .replace('"', '\"')
                for study_id_and_gse in study_ids_and_geos
            ]

            _store_test_request(database_holder, request_id, _S_QUERY['query'])

            inserted_geo_study_ids = []
            for study_id_and_gse in study_ids_and_geos:
                inserted_geo_study_ids.append(_store_test_geo_study(database_holder, request_id, study_id_and_gse[0], study_id_and_gse[1]))

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            inserted_geo_study_ids_for_sql_in = ','.join(map(str, inserted_geo_study_ids))

            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id in ({inserted_geo_study_ids_for_sql_in})
                                    ''')
            actual_ok_rows = database_cursor.fetchall()
            expected_ok_rows = [(srp,) for srp in srps]
            assert actual_ok_rows == expected_ok_rows

            database_cursor.execute(f'select * from sracollector_dev.sra_project_missing where geo_study_id in ({inserted_geo_study_ids_for_sql_in})')
            actual_ko_rows = database_cursor.fetchall()
            assert actual_ko_rows == []

            # THEN REGARDING MESSAGES
            assert mock_sqs.send_message.call_count == len(srps)

            study_ids_and_gses_and_srps = list(zip(study_ids_and_geos, srps))

            expected_calls = [
                call(QueueUrl=E_get_study_srp.output_sqs, MessageBody=json.dumps({
                    'request_id': request_id,
                    'srp': study_id_and_gse_and_srp[1]
                }))
                for study_id_and_gse_and_srp in study_ids_and_gses_and_srps
            ]

            actual_calls = mock_sqs.send_message.call_args_list

            assert expected_calls == actual_calls


def test_e_get_study_srp_ko(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs_send_message:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            mock_sqs_send_message.send_message = Mock()
            function_name = 'E_get_study_srp'

            study_ids = [200110021, 20037005, 200225606]
            gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]

            def multiple_error_raised(parameter):
                pysradb_errors = [AttributeError('here will go'), ValueError('an explanation'), KeyError('of the issue')]
                gse_to_srp_mapping = dict(zip(gses, pysradb_errors))
                error = gse_to_srp_mapping.get(parameter)
                raise error

            mock_sra_web_gse_to_srp.side_effect = multiple_error_raised

            request_id = _provide_random_request_id()

            study_ids_and_gses = list(zip(study_ids, gses))

            input_bodies = [
                json.dumps({'request_id': request_id, 'gse': study_id_and_gse[1]})
                .replace('"', '\"')
                for study_id_and_gse in study_ids_and_gses
            ]

            _store_test_request(database_holder, request_id, _S_QUERY['query'])

            inserted_geo_study_ids = []
            for study_id_and_gse in study_ids_and_gses:
                inserted_geo_study_ids.append(_store_test_geo_study(database_holder, request_id, study_id_and_gse[0], study_id_and_gse[1]))

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            inserted_geo_study_ids_for_sql_in = ','.join(map(str, inserted_geo_study_ids))

            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id in ({inserted_geo_study_ids_for_sql_in})
                                    ''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            pysradb_errors_for_sql_in = ','.join(["'ATTRIBUTE_ERROR'", "'VALUE_ERROR'", "'KEY_ERROR'"])
            database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='gse_to_srp' and name in ({pysradb_errors_for_sql_in})")
            pysradb_error_reference_ids = [pysradb_error_reference_row[0] for pysradb_error_reference_row in database_cursor.fetchall()]
            expected_details = ['here will go', 'an explanation', "'of the issue'"]

            database_cursor.execute(f'select pysradb_error_reference_id, details from sracollector_dev.sra_project_missing where geo_study_id in ({inserted_geo_study_ids_for_sql_in})')
            actual_ko_rows = database_cursor.fetchall()
            expected_ko_rows = list(zip(pysradb_error_reference_ids, expected_details))
            assert actual_ko_rows == expected_ko_rows

            # THEN REGARDING MESSAGES
            assert mock_sqs_send_message.send_message.call_count == 0


def test_e_get_study_srp_skip_already_linked_gse(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message = Mock()
        function_name = 'E_get_study_srp'

        request_id = _provide_random_request_id()
        study_ids = [20094225, 20094169]
        gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
        srp = 'SRP094854'

        _store_test_request(database_holder, request_id, _S_QUERY['query'])
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
        actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), Context(function_name))

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
        assert mock_sqs_send_message.send_message.call_count == 1
        mock_sqs_send_message.send_message.assert_called_with(
            QueueUrl=E_get_study_srp.output_sqs,
            MessageBody=json.dumps({'request_id': request_id, 'srp': srp})
        )  # TODO todos los que se salta la BBDD, aseverar q el mensaje sí se envia


def test_e_get_study_srp_skip_already_processed_geo(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message = Mock()
        function_name = 'E_get_study_srp'

        request_id = _provide_random_request_id()
        study_id = 200126815
        gse = str(study_id).replace('200', 'GSE', 3)
        srp = 'SRP185522'

        input_body = json.dumps({'request_id': request_id, 'gse': gse}).replace('"', '\"')

        _store_test_request(database_holder, request_id, _S_QUERY['query'])
        inserted_geo_study_id = _store_test_geo_study(database_holder, request_id, study_id, gse)
        inserted_sra_project_id = _store_test_sra_project(database_holder, srp, inserted_geo_study_id)

        # WHEN
        actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs([input_body]), Context(function_name))

        # THEN REGARDING LAMBDA
        assert actual_result == {'batchItemFailures': []}

        # THEN REGARDING DATA
        database_cursor, _ = database_holder
        database_cursor.execute(f'select srp from sracollector_dev.sra_project where id={inserted_sra_project_id}')
        actual_ok_rows = database_cursor.fetchall()
        assert actual_ok_rows == [(srp,)]

        database_cursor.execute(f'select pysradb_error_reference_id from sracollector_dev.sra_project_missing where geo_study_id={inserted_geo_study_id}')
        actual_ko_rows = database_cursor.fetchall()
        assert actual_ko_rows == []

        # THEN REGARDING MESSAGES
        assert mock_sqs_send_message.send_message.call_count == 0


def test_e_get_study_srp_skip_unexpected_results(database_holder):
    with patch.object(E_get_study_srp, 'sqs') as mock_sqs_send_message:
        with patch.object(E_get_study_srp.SRAweb, 'gse_to_srp') as mock_sra_web_gse_to_srp:
            # GIVEN
            mock_sqs_send_message.send_message = Mock()
            function_name = 'E_get_study_srp'

            request_id = _provide_random_request_id()
            study_ids = [20040034, 200252323, 20030614]
            gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]

            def multiple_return_values(parameter):
                unexpected_results = [{'study_accession': [srp]} for srp in ['SRX029072', 'DRP010911', 'ERP000531']]
                gse_to_srp_mapping = dict(zip(gses, unexpected_results))
                return gse_to_srp_mapping.get(parameter, 'default_return_value')

            mock_sra_web_gse_to_srp.side_effect = multiple_return_values

            study_ids_and_gses = list(zip(study_ids, gses))

            input_bodies = [
                json.dumps({'request_id': request_id, 'gse': study_id_and_gse[1]})
                .replace('"', '\"')
                for study_id_and_gse in study_ids_and_gses
            ]

            _store_test_request(database_holder, request_id, _S_QUERY['query'])

            inserted_geo_study_ids = []
            for study_id_and_gse in study_ids_and_gses:
                inserted_geo_study_ids.append(_store_test_geo_study(database_holder, request_id, study_id_and_gse[0], study_id_and_gse[1]))

            # WHEN
            actual_result = E_get_study_srp.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            inserted_geo_study_ids_for_sql_in = ','.join(map(str, inserted_geo_study_ids))

            database_cursor.execute(f'''select srp from sracollector_dev.sra_project
                                        join sracollector_dev.geo_study_sra_project_link on id = sra_project_id
                                        where geo_study_id in ({inserted_geo_study_ids_for_sql_in})
                                    ''')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(f'select * from sracollector_dev.sra_project_missing where geo_study_id in ({inserted_geo_study_ids_for_sql_in})')
            actual_ko_rows = database_cursor.fetchall()
            assert actual_ko_rows == []

            # THEN REGARDING MESSAGES
            assert mock_sqs_send_message.send_message.call_count == 0


def test_f_get_study_srrs_ok(database_holder):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs_send_message:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr') as mock_sra_web_srp_to_srr:
            # GIVEN
            mock_sqs_send_message.send_message_batch = Mock()
            function_name = 'F_get_study_srrs'

            request_id = _provide_random_request_id()
            study_ids = [200126815, 200308347]
            gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
            srps = ['SRP414713', 'SRP308347']
            study_ids_and_gses_and_srps = list(zip(study_ids, gses, srps))
            srrs_for_srp414713 = ['SRR22873806', 'SRR22873807', 'SRR22873808', 'SRR22873809', 'SRR22873810', 'SRR22873811', 'SRR22873812', 'SRR22873813', 'SRR22873814']
            srrs_for_srp308347 = ['SRR13790583', 'SRR13790584', 'SRR13790585', 'SRR13790586', 'SRR13790587', 'SRR13790588', 'SRR13790589', 'SRR13790590', 'SRR13790591', 'SRR13790592',
                                  'SRR13790593', 'SRR13790594']

            def multiple_return_values(parameter):
                srr_results = [{'run_accession': srrs_for_srp414713},
                               {'run_accession': srrs_for_srp308347}]
                gse_to_srp_mapping = dict(zip(srps, srr_results))
                return gse_to_srp_mapping.get(parameter, 'default_return_value')

            mock_sra_web_srp_to_srr.side_effect = multiple_return_values

            input_bodies = [
                json.dumps({
                    'request_id': request_id,
                    'srp': study_id_and_gse_and_srp[2]
                }).replace('"', '\"')
                for study_id_and_gse_and_srp in study_ids_and_gses_and_srps
            ]

            _store_test_request(database_holder, request_id, _S_QUERY['query'])
            inserted_geo_study_ids = []
            for study_id_and_gse_and_srp in study_ids_and_gses_and_srps:
                inserted_geo_study_ids.append(_store_test_geo_study(database_holder, request_id, study_id_and_gse_and_srp[0], study_id_and_gse_and_srp[1]))

            inserted_sra_project_ids = []
            for index, study_id_and_gse_and_srp in enumerate(study_ids_and_gses_and_srps):
                inserted_sra_project_ids.append(_store_test_sra_project(database_holder, study_id_and_gse_and_srp[2], inserted_geo_study_ids[index]))

            # WHEN
            actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            inserted_sra_project_id_for_sql_in = ','.join(map(str, inserted_sra_project_ids))
            database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
            actual_ok_rows = database_cursor.fetchall()
            actual_ok_rows = actual_ok_rows.sort()
            expected_rows = [(srr,) for srr in (srrs_for_srp414713, srrs_for_srp308347)]
            expected_rows = expected_rows.sort()
            assert actual_ok_rows == expected_rows

            database_cursor.execute(f'select * from sracollector_dev.sra_run_missing where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
            actual_ko_rows = database_cursor.fetchall()
            assert actual_ko_rows == []

            # THEN REGARDING MESSAGES
            expected_calls = [
                f'{{"request_id": "{request_id}", "srr": "{srr}"}}'
                for srr in srrs_for_srp308347
            ] + [
                f'{{"request_id": "{request_id}", "srr": "{srr}"}}'
                for srr in srrs_for_srp414713
            ]

            assert mock_sqs_send_message.send_message_batch.call_count == _get_needed_batches_of_ten_messages(len(srrs_for_srp414713)+len(srrs_for_srp308347))

            actual_calls_entries = [arg.kwargs['Entries'] for arg in mock_sqs_send_message.send_message_batch.call_args_list]
            actual_calls_message_bodies = [item['MessageBody'] for sublist in actual_calls_entries for item in sublist]

            assert expected_calls.sort() == actual_calls_message_bodies.sort()


def test_f_get_study_srrs_ko(database_holder):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs_send_message:
        with patch.object(E_get_study_srp.SRAweb, 'srp_to_srr') as mock_sra_web_srp_to_srr:
            # GIVEN
            mock_sqs_send_message.send_message_batch = Mock()
            function_name = 'F_get_study_srrs'

            request_id = _provide_random_request_id()
            study_ids = [200126815, 200118257]
            gses = [str(study_id).replace('200', 'GSE', 3) for study_id in study_ids]
            srps = ['SRP185522', 'SRP178139']
            study_ids_and_gses_and_srps = list(zip(study_ids, gses, srps))

            def multiple_error_raised(parameter):
                pysradb_errors = [AttributeError("'NoneType' object has no attribute 'columns'"), AttributeError("'NoneType' object has no attribute 'columns'")]
                srp_to_srr_mapping = dict(zip(srps, pysradb_errors))
                error = srp_to_srr_mapping.get(parameter)
                raise error

            mock_sra_web_srp_to_srr.side_effect = multiple_error_raised

            input_bodies = [
                json.dumps({
                    'request_id': request_id,
                    'srp': study_id_and_gse_and_srp[2]
                }).replace('"', '\"')
                for study_id_and_gse_and_srp in study_ids_and_gses_and_srps
            ]

            _store_test_request(database_holder, request_id, _S_QUERY['query'])
            inserted_geo_study_ids = []
            for study_id_and_gse_and_srp in study_ids_and_gses_and_srps:
                inserted_geo_study_ids.append(_store_test_geo_study(database_holder, request_id, study_id_and_gse_and_srp[0], study_id_and_gse_and_srp[1]))

            inserted_sra_project_ids = []
            for index, study_id_and_gse_and_srp in enumerate(study_ids_and_gses_and_srps):
                inserted_sra_project_ids.append(_store_test_sra_project(database_holder, study_id_and_gse_and_srp[2], inserted_geo_study_ids[index]))

            # WHEN
            actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs(input_bodies), Context(function_name))

            # THEN REGARDING LAMBDA
            assert actual_result == {'batchItemFailures': []}

            # THEN REGARDING DATA
            database_cursor, _ = database_holder
            inserted_sra_project_id_for_sql_in = ','.join(map(str, inserted_sra_project_ids))
            database_cursor.execute(f'select srr from sracollector_dev.sra_run where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
            actual_ok_rows = database_cursor.fetchall()
            assert actual_ok_rows == []

            database_cursor.execute(f"select id from sracollector_dev.pysradb_error_reference where operation='srp_to_srr' and name='ATTRIBUTE_ERROR'")
            pysradb_error_reference_id = database_cursor.fetchone()[0]
            expected_detail = "'NoneType' object has no attribute 'columns'"

            database_cursor.execute(f'select pysradb_error_reference_id, details from sracollector_dev.sra_run_missing where sra_project_id in ({inserted_sra_project_id_for_sql_in})')
            actual_ko_rows = database_cursor.fetchall()
            assert actual_ko_rows == [(pysradb_error_reference_id, expected_detail), (pysradb_error_reference_id, expected_detail)]

            # THEN REGARDING MESSAGES
            assert mock_sqs_send_message.send_message_batch.call_count == 0


def test_f_get_study_srrs_skip_already_processed_srp(database_holder):
    with patch.object(F_get_study_srrs, 'sqs') as mock_sqs_send_message:
        # GIVEN
        mock_sqs_send_message.send_message_batch = Mock()
        function_name = 'F_get_study_srrs'

        request_id = _provide_random_request_id()
        study_id = 200126815
        gse = str(study_id).replace('200', 'GSE', 3)
        srp = 'SRP185522'
        srr = 'SRR787899'

        input_body = json.dumps({'request_id': request_id, 'srp': srp})

        _store_test_request(database_holder, request_id, _S_QUERY['query'])
        geo_study_id = _store_test_geo_study(database_holder, request_id, study_id, gse)
        sra_project_id = _store_test_sra_project(database_holder, srp, geo_study_id)
        _store_test_sra_run(database_holder, srr, sra_project_id)

        # WHEN
        actual_result = F_get_study_srrs.handler(_get_customized_input_from_sqs([input_body]), Context(function_name))

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
        assert mock_sqs_send_message.send_message_batch.call_count == 0
