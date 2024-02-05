import json
import logging

import boto3
from env_params import env_params
from postgres_connection import postgres_connection
from pysradb import SRAweb

sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    output_sqs, schema = env_params.params_per_env(context.function_name)

    try:
        if event:
            request_id = json.loads(event['Records'][0]['body'])['request_id']
            logging.info(f'Received event {event}')
            for record in event['Records']:
                study_with_missing_srrs = json.loads(record['body'])
                logging.debug(f'Received event {study_with_missing_srrs}')

                srp = study_with_missing_srrs['srp']
                gse = study_with_missing_srrs['gse']
                request_id = study_with_missing_srrs['request_id']

                study_id = study_with_missing_srrs['study_id']

                try:
                    raw_pysradb_data_frame = SRAweb().srp_to_srr(srp)
                    srrs = list(raw_pysradb_data_frame['run_accession'])

                    if srrs:
                        logging.info(f'For study {study_id} with {gse} and {srp}, SRRs are {srrs}')
                        for srr in srrs:
                            response = json.dumps({**study_with_missing_srrs, 'srr': srr})
                            sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                            _store_srr_in_db(schema, srr, request_id, srp)
                            logging.info(f'Sent event to {output_sqs} with body {response}')
                    else:
                        logging.info(f'No SRR for study {study_id}, {gse} and {srp} found via pysradb')
                except AttributeError as attribute_error:  ## TODO split to a F2_* link 2 DLQ?
                    logging.error(f'For study {study_id} with {gse} and srp {srp}, pysradb produced attribute error with name {attribute_error.name}')
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')


def _store_srr_in_db(schema: str, srr: str, request_id: str, srp: str):
    try:
        database_connection = postgres_connection.get_connection()
        sra_project_id = _get_id_sra_project(schema, request_id, srp)
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            f'insert into {schema}.sra_run (srr, sra_project_id) values (%s, %s)',
            (srr, sra_project_id)
        )
        logging.debug(f'Executing: {statement}...')
        cursor.execute(statement)
        logging.info(f'Inserted sra run info in database')
        database_connection.commit()
        cursor.close()
        database_connection.close()
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')


def _get_id_sra_project(schema: str, request_id: str, srp: str):
    try:
        database_connection = postgres_connection.get_connection()
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            f'''
            select sp.id from {schema}.sra_project sp
            join {schema}.geo_study gs on gs.id = sp.geo_study_id
            where gs.request_id=%s and srp=%s
            ''',
            (request_id, srp)
        )
        logging.debug(f'Executing: {statement}...')
        cursor.execute(statement)
        sra_project_id = cursor.fetchone()
        logging.info(f'Selected the sra_project row with id {sra_project_id}')
        cursor.close()
        database_connection.close()
        return sra_project_id
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
