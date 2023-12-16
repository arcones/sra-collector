import json
import logging

import boto3
from pysradb import SRAweb

sqs = boto3.client('sqs', region_name='eu-central-1')
ssm = boto3.client('ssm', region_name='eu-central-1')

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/srps_queue'

def _define_log_level():
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']
    the_logger = logging.getLogger('get_study_srp')
    logging.basicConfig(format='%(levelname)s %(message)s')

    if log_level == 'DEBUG':
        the_logger.setLevel(logging.DEBUG)
    else:
        the_logger.setLevel(logging.INFO)

    return the_logger


logger = _define_log_level()

def handler(event, context):
    if event:
        logger.debug(f'Received event {event}')
        for record in event['Records']:
            study_with_missing_srp = json.loads(record['body'])
            logger.debug(f'Received event {study_with_missing_srp}')

            gse = study_with_missing_srp['gse']
            raw_pysradb_response = SRAweb().gse_to_srp(gse)
            logger.debug(f'Raw pysradb response for {gse} is {raw_pysradb_response}')
            srp = raw_pysradb_response['study_accession'][0]  ## TODO manage two SRPs scenario

            if srp:
                logger.info(f"SRP {srp} for GSE {gse} retrieved via pysradb for study {study_with_missing_srp['study_id']}, pushing message to study summaries queue")
                response = json.dumps({**study_with_missing_srp, 'srps': [srp]})
                sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                logger.debug(f'Sent event to {output_sqs} with body {response}')
