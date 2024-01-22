import json
import logging

import boto3
from postgres_connection import postgres_connection
from pysradb import SRAweb
# from lambda_log_support import lambda_log_support


sqs = boto3.client('sqs', region_name='eu-central-1')

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/srrs_queue'


def handler(event, context):
    try:
        if event:
            request_id = json.loads(event['Records'][0]['body'])['request_id']
            # lambda_log_support.configure_logger(request_id, context.aws_request_id)
            logging.info(f'Received event {event}')
            for record in event['Records']:
                study_with_missing_srrs = json.loads(record['body'])
                logging.info(f'Received event {study_with_missing_srrs}')

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
                            _store_srr_in_db(srr, request_id, srp)
                            logging.info(f'Sent event to {output_sqs} with body {response}')
                    else:
                        logging.info(f'No SRR for study {study_id}, {gse} and {srp} found via pysradb')
                except AttributeError as attribute_error: ## TODO split to a F2_* link 2 DLQ?
                    logging.error(f'For study {study_id} with {gse} and srp {srp}, pysradb produced attribute error with name {attribute_error.name}')
    except:
        logging.exception(f'An exception has occurred')

def _store_srr_in_db(srr: str, request_id: str, srp: str):
    try:
        database_connection = postgres_connection.get_connection()
        sra_project_id = _get_id_sra_project(request_id, srp)
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            'insert into sra_run (srr, sra_project_id) values (%s, %s)',
            (srr, sra_project_id)
        )
        logging.debug(f'Executing: {statement}...')
        cursor.execute(statement)
        logging.info(f'Inserted sra run info in database')
        database_connection.commit()
        cursor.close()
        database_connection.close()
    except:
        logging.exception(f'An exception has occurred')


def _get_id_sra_project(request_id: str, srp: str):
    try:
        database_connection = postgres_connection.get_connection()
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            '''
            select sp.id from sra_project sp
            join geo_study gs on gs.id = sp.geo_study_id
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
    except:
        logging.exception(f'An exception has occurred')
