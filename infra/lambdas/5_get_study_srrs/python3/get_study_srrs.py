import json
import logging

import boto3
from pysradb import SRAweb

sqs = boto3.client('sqs', region_name='eu-central-1')
ssm = boto3.client('ssm', region_name='eu-central-1')

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/srrs_queue'


def _define_log_level():
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']
    the_logger = logging.getLogger('get_study_srrs')
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
            study_with_missing_srrs = json.loads(record['body'])
            logger.debug(f'Received event {study_with_missing_srrs}')

            srp = study_with_missing_srrs['srps'][0] ## TODO manage two SRPs scenario
            gse = study_with_missing_srrs['gse']
            study_id = study_with_missing_srrs['study_id']

            raw_pysradb_data_frame = SRAweb().srp_to_srr(srp)
            logger.debug(f'Raw pysradb response for {srp} is {raw_pysradb_data_frame}')
            srrs = list(raw_pysradb_data_frame['run_accession'])

            if srrs:
                logger.info(f'For study {study_id} with {gse} and SRP {srp}, SRRs are {srrs}')
                for srr in srrs:
                    response = json.dumps({**study_with_missing_srrs, 'srr': srr})
                    sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                    logger.debug(f'Sent event to {output_sqs} with body {response}')
