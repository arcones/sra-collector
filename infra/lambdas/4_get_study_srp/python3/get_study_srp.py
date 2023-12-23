import json

import boto3
from lambda_log_support import lambda_log_support
from postgres_connection import postgres_connection
from pysradb import SRAweb

sqs = boto3.client('sqs', region_name='eu-central-1')

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/srps_queue'

logger = lambda_log_support.define_log_level()

def handler(event, context):
    if event:
        logger.debug(f'Received event {event}')
        for record in event['Records']:
            study_with_missing_srp = json.loads(record['body'])
            logger.debug(f'Received event {study_with_missing_srp}')

            gse = study_with_missing_srp['gse']
            raw_pysradb_response = SRAweb().gse_to_srp(gse)
            logger.debug(f'Raw pysradb response for {gse} is {raw_pysradb_response}')
            srp = raw_pysradb_response['study_accession'][0]

            if srp:
                logger.info(f"SRP {srp} for GSE {gse} retrieved via pysradb for study {study_with_missing_srp['study_id']}, pushing message to study summaries queue")
                response = json.dumps({**study_with_missing_srp, 'srp': srp})
                sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                logger.debug(f'Sent event to {output_sqs} with body {response}')

## TODO ME HE QUEDADO APAÑANDO ESTE METODO
def _store_srp_in_db(study_id: str, request_id: str, accession: str):
    database_connection = postgres_connection.get_connection()
    cursor = database_connection.cursor()
    statement = cursor.mogrify(
        'insert into sra_project (srp, request_id, geo_study_id) values (%s, %s, %s)',
        (study_id, request_id, accession)
    )
    logger.debug(f'Executing: {statement}...')
    cursor.execute(statement)
    logger.debug(f'Inserted geo study info in database')
    database_connection.commit()
    cursor.close()
    database_connection.close()
