import json
import logging

import boto3
from env_params import env_params
from postgres_connection import postgres_connection
from pysradb import SRAweb

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    try:
        output_sqs, schema = env_params.params_per_env(context.function_name)
        if event:
            for record in event['Records']:
                request_body = json.loads(record['body'])

                logging.info(f'Received event {request_body}')

                srp = request_body['srp']
                gse = request_body['gse']
                request_id = request_body['request_id']

                study_id = request_body['study_id']

                try:
                    raw_pysradb_data_frame = SRAweb().srp_to_srr(srp)
                    srrs = list(raw_pysradb_data_frame['run_accession'])

                    if srrs:
                        logging.info(f'For study {study_id} with {gse} and {srp}, SRRs are {srrs}')

                        for srr in srrs:
                            response = json.dumps({**request_body, 'srr': srr})
                            sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                            logging.info(f'Sent event to {output_sqs} with body {response}')

                        _store_srrs_in_db(schema, srrs, request_id, srp)
                    else:
                        logging.info(f'No SRR for study {study_id}, {gse} and {srp} found via pysradb')
                except AttributeError as attribute_error:  ## TODO split to a F2_* link 2 DLQ?
                    logging.error(f'For study {study_id} with {gse} and srp {srp}, pysradb produced attribute error with name {attribute_error.name}')
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _store_srrs_in_db(schema: str, srrs: [str], request_id: str, srp: str):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        sra_project_id = _get_id_sra_project(schema, request_id, srp)
        srr_and_sra_id_tuples = [(srr, sra_project_id) for srr in srrs]
        logging.info(f'Tuples to insert {srr_and_sra_id_tuples}')
        statement = f'insert into {schema}.sra_run (srr, sra_project_id) values (%s, %s)'
        postgres_connection.execute_bulk_write_statement(database_connection, database_cursor, statement, srr_and_sra_id_tuples)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _get_id_sra_project(schema: str, request_id: str, srp: str):
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
