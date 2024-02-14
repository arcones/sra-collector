import json
import logging
from enum import Enum

import boto3
from env_params import env_params
from postgres_connection import postgres_connection
from pysradb import SRAweb

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)


class PysradbError(Enum):
    ATTRIBUTE_ERROR = 'ATTRIBUTE_ERROR'
    VALUE_ERROR = 'VALUE_ERROR'
    KEY_ERROR = 'KEY_ERROR'
    NOT_FOUND = 'NOT_FOUND'


sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    try:
        output_sqs, schema = env_params.params_per_env(context.function_name)
        if event:
            logging.info(f'Received {len(event["Records"])} records event {event}')
            for record in event['Records']:
                request_body = json.loads(record['body'])

                logging.info(f'Processing record {request_body}')

                study_id = request_body['study_id']
                request_id = request_body['request_id']
                gse = request_body['gse']

                # if _is_srp_pending_to_be_processed(schema, request_id, gse):
                try:
                    raw_pysradb_response = SRAweb().gse_to_srp(gse)
                    srp = raw_pysradb_response['study_accession'][0]

                    if srp:
                        logging.info(f'SRP {srp} for GSE {gse} retrieved via pysradb for study {study_id}, pushing message to study summaries queue')
                        response = json.dumps({**request_body, 'srp': srp})
                        _store_srp_in_db(schema, request_id, gse, srp)
                        sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                        logging.info(f'Sent event to {output_sqs} with body {response}')
                    else:
                        logging.info(f'No SRP for {study_id} and {gse} found via pysradb')
                        _store_missing_srp_in_db(schema, request_id, srp, PysradbError.NOT_FOUND, 'No SRP found')
                except AttributeError as attribute_error:
                    logging.info(f'For study {study_id} with {gse}, pysradb produced attribute error with name {attribute_error.name}')
                    _store_missing_srp_in_db(schema, request_id, gse, PysradbError.ATTRIBUTE_ERROR, str(attribute_error))
                except ValueError as value_error:
                    logging.info(f'For study {study_id} with {gse}, pysradb produced value error: {value_error}')
                    _store_missing_srp_in_db(schema, request_id, gse, PysradbError.VALUE_ERROR, str(value_error))
                except KeyError as key_error:
                    logging.info(f'For study {study_id} with {gse}, pysradb produced key error: {key_error}')
                    _store_missing_srp_in_db(schema, request_id, gse, PysradbError.KEY_ERROR, str(key_error))
                # else:
                #     logging.info(f'The record with {request_id} and {gse} has already been processed')
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        return {'statusCode': 500}


def _store_srp_in_db(schema: str, request_id: str, gse: str, srp: str):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        sra_project_id = _get_id_sra_project(schema, srp)
        if not sra_project_id:
            statement = database_cursor.mogrify(f'insert into {schema}.sra_project (srp) values (%s) returning id;', (srp,))
            sra_project_id = postgres_connection.execute_write_statement_returning(database_connection, database_cursor, statement)

        geo_study_id = _get_id_geo_study(schema, request_id, gse)
        statement = database_cursor.mogrify(
            f'insert into {schema}.geo_study_sra_project_link (geo_study_id, sra_project_id) values (%s, %s);',
            (geo_study_id, sra_project_id)
        )
        postgres_connection.execute_write_statement(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _get_id_sra_project(schema: str, srp: str) -> int:
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(f'select id from {schema}.sra_project where srp=%s', (srp,))
        return postgres_connection.execute_read_statement_for_primary_key(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred in {_get_id_sra_project.__name__} function: {str(exception)}')
        raise exception


def _store_missing_srp_in_db(schema: str, request_id: str, gse: str, pysradb_error: PysradbError, details: str):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        geo_study_id = _get_id_geo_study(schema, request_id, gse)
        pysradb_error_reference_id = _get_pysradb_error_reference(schema, pysradb_error)
        statement = database_cursor.mogrify(
            f'insert into {schema}.sra_project_missing (geo_study_id, pysradb_error_reference_id, details) values (%s, %s, %s);',
            (geo_study_id, pysradb_error_reference_id, details)
        )
        postgres_connection.execute_write_statement(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _get_id_geo_study(schema: str, request_id: str, gse: str) -> int:
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(f'select id from {schema}.geo_study where request_id=%s and gse=%s', (request_id, gse))
        return postgres_connection.execute_read_statement_for_primary_key(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _get_pysradb_error_reference(schema: str, pysradb_error: PysradbError) -> int:
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(f"select id from {schema}.pysradb_error_reference where name=%s and operation='gse_to_srp'", (pysradb_error.value,))
        return postgres_connection.execute_read_statement_for_primary_key(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception

# def _is_srp_pending_to_be_processed(schema: str, request_id: str, gse: str) -> bool: TODO Y QUITAR TODAS SUS HERMANAS.... IGUAL TIENE QUE SER FIFO...
#     try:
#         geo_study_id = _get_id_geo_study(schema, request_id, gse)
#         database_connection, database_cursor = postgres_connection.get_database_holder()
#         statement = database_cursor.mogrify(
#             f'''
#             select id from {schema}.sra_project where geo_study_id=%s
#             union
#             select id from {schema}.sra_project_missing where geo_study_id=%s
#             ''',
#             (geo_study_id, geo_study_id)
#         )
#         return not postgres_connection.is_row_present(database_connection, database_cursor, statement)
#     except Exception as exception:
#         logging.error(f'An exception has occurred: {str(exception)}')
#         raise exception
