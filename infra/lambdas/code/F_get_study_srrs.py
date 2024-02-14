import json
import logging
import time
from enum import Enum

import boto3
from env_params import env_params
from postgres_connection import postgres_connection
from pysradb import SRAweb

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')

class PysradbError(Enum):
    ATTRIBUTE_ERROR = 'ATTRIBUTE_ERROR'
    NOT_FOUND = 'NOT_FOUND'

def handler(event, context):
    try:
        output_sqs, schema = env_params.params_per_env(context.function_name)
        if event:
            logging.info(f'Received {len(event["Records"])} records event {event}')
            for record in event['Records']:
                request_body = json.loads(record['body'])

                logging.info(f'Processing record {request_body}')

                srp = request_body['srp']
                gse = request_body['gse']
                request_id = request_body['request_id']

                study_id = request_body['study_id']

                if _is_srr_pending_to_be_processed(schema, request_id, srp):

                    try:
                        raw_pysradb_data_frame = SRAweb().srp_to_srr(srp)
                        srrs = list(raw_pysradb_data_frame['run_accession'])

                        if srrs:
                            logging.info(f'For study {study_id} with {gse} and {srp}, SRRs are {srrs}')

                            messages = []

                            for srr in srrs:
                                messages.append({
                                    'Id': str(time.time()).replace('.', ''),
                                    'MessageBody': json.dumps({**request_body, 'srr': srr})
                                })

                            _store_srrs_in_db(schema, srrs, request_id, srp)

                            message_batches = [messages[index:index + 10] for index in range(0, len(messages), 10)]
                            for message_batch in message_batches:
                                sqs.send_message_batch(QueueUrl=output_sqs, Entries=message_batch)

                            logging.info(f'Sent {len(messages)} messages to {output_sqs.split("/")[-1]}')
                        else:
                            logging.info(f'No SRR for study {study_id}, {gse} and {srp} found via pysradb')
                            _store_missing_srr_in_db(schema, request_id, srp, PysradbError.NOT_FOUND, 'No SRR found')
                    except AttributeError as attribute_error:
                        logging.info(f'For study {study_id} with {gse} and srp {srp}, pysradb produced attribute error with name {attribute_error.name}')
                        _store_missing_srr_in_db(schema, request_id, srp, PysradbError.ATTRIBUTE_ERROR, str(attribute_error))
                else:
                    logging.info(f'The record with {request_id} and {srp} has already been processed')
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        return {
            'statusCode': 500  # TODO  parece q es necesario en cualquier error: ver sam-cli
        }

def _store_srrs_in_db(schema: str, srrs: [str], request_id: str, srp: str):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        sra_project_id = _get_id_sra_project(schema, request_id, srp)
        srr_and_sra_id_tuples = [(srr, sra_project_id) for srr in srrs]
        logging.info(f'Tuples to insert {srr_and_sra_id_tuples}')
        postgres_connection.execute_bulk_write_statement(database_connection, database_cursor, schema, 'sra_run', ['srr', 'sra_project_id'], srr_and_sra_id_tuples)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _get_id_sra_project(schema: str, request_id: str, srp: str) -> int:
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(
            f'''
            select sp.id from {schema}.sra_project sp
            join {schema}.geo_study gs on gs.id = sp.geo_study_id
            where gs.request_id=%s and srp=%s
            ''',
            (request_id, srp)
        )
        return postgres_connection.execute_read_statement_for_primary_key(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _store_missing_srr_in_db(schema: str, request_id: str, srp: str, pysradb_error: PysradbError, details: str):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        sra_project_id = _get_id_sra_project(schema, request_id, srp)
        pysradb_error_reference_id = _get_pysradb_error_reference(schema, pysradb_error)
        statement = database_cursor.mogrify(
            f'insert into {schema}.sra_run_missing (sra_project_id, pysradb_error_reference_id, details) values (%s, %s, %s);',
            (sra_project_id, pysradb_error_reference_id, details)
        )
        postgres_connection.execute_write_statement(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _get_pysradb_error_reference(schema: str, pysradb_error: PysradbError) -> int:
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(f"select id from {schema}.pysradb_error_reference where name=%s and operation='srp_to_srr'", (pysradb_error.value,))
        return postgres_connection.execute_read_statement_for_primary_key(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _is_srr_pending_to_be_processed(schema: str, request_id: str, srp: str) -> bool:
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        sra_project_id = _get_id_sra_project(schema, request_id, srp)
        statement = database_cursor.mogrify(
            f'''
            select id from {schema}.sra_run where sra_project_id=%s
            union
            select id from {schema}.sra_run_missing where sra_project_id=%s
            ''',
            (sra_project_id, sra_project_id)
        )
        return not postgres_connection.is_row_present(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
