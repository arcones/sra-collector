import json

import boto3
from lambda_log_support import lambda_log_support
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
            study_id = study_with_missing_srrs['study_id']

            raw_pysradb_data_frame = SRAweb().srp_to_srr(srp)
            logger.debug(f'Raw pysradb response for {srp} is {raw_pysradb_data_frame}')
            srrs = list(raw_pysradb_data_frame['run_accession'])

            if srrs:
                logger.info(f'For study {study_id} with {gse} and {srp}, SRRs are {srrs}')
                for srr in srrs:
                    response = json.dumps({**study_with_missing_srrs, 'srr': srr})
                    sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                    logger.debug(f'Sent event to {output_sqs} with body {response}')
