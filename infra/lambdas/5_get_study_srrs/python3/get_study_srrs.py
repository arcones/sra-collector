import json

import boto3
from lambda_log_support import lambda_log_support
from postgres_connection import postgres_connection
from pysradb import SRAweb

sqs = boto3.client('sqs', region_name='eu-central-1')

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/srrs_queue'

logger = lambda_log_support.define_log_level()


def handler(event, context):
    if event:
        logger.debug(f'Received event {event}')
        for record in event['Records']:
            study_with_missing_srrs = json.loads(record['body'])
            logger.debug(f'Received event {study_with_missing_srrs}')

            srp = study_with_missing_srrs['srp']
            gse = study_with_missing_srrs['gse']
            request_id = study_with_missing_srrs['request_id']

            study_id = study_with_missing_srrs['study_id']

            raw_pysradb_data_frame = SRAweb().srp_to_srr(srp)
            logger.debug(f'Raw pysradb response for {srp} is {raw_pysradb_data_frame}')
            srrs = list(raw_pysradb_data_frame['run_accession'])

            if srrs:
                logger.info(f'For study {study_id} with {gse} and {srp}, SRRs are {srrs}')
                for srr in srrs:
                    response = json.dumps({**study_with_missing_srrs, 'srr': srr})
                    sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                    _store_srr_in_db(srr, request_id, srp)
                    logger.debug(f'Sent event to {output_sqs} with body {response}')


def _store_srr_in_db(srr: str, request_id: str, srp: str):
    database_connection = postgres_connection.get_connection()
    sra_project_id = _get_id_sra_project(request_id, srp)
    cursor = database_connection.cursor()
    statement = cursor.mogrify(
        'insert into sra_run (srr, sra_project_id) values (%s, %s)',
        (srr, sra_project_id)
    )
    logger.debug(f'Executing: {statement}...')
    cursor.execute(statement)
    logger.debug(f'Inserted sra run info in database')
    database_connection.commit()
    cursor.close()
    database_connection.close()


def _get_id_sra_project(request_id: str, srp: str):
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
    logger.debug(f'Executing: {statement}...')
    cursor.execute(statement)
    sra_project_id = cursor.fetchone()
    logger.debug(f'Selected the sra_project row with id {sra_project_id}')
    cursor.close()
    database_connection.close()
    return sra_project_id
