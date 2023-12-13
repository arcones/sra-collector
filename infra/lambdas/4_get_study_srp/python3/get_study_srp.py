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

            try:
                srp = SRAweb().gse_to_srp(gse)['study_accession'][0]  ## TODO manage two SRPs scenario
                logger.debug(f'For {gse} the SRP is {srp}')

                if srp:
                    logger.info(f"SRP retrieved via pysradb for {study_with_missing_srp['study_id']}, pushing message to study summaries queue")
                    response = json.dumps({**study_with_missing_srp, 'srps': [srp]})
                    sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                    logger.debug(f'Sent event to {output_sqs} with body {response}')
            except AttributeError as attribute_error:
                event['pysradb_failure_reason'] = 'PYSRADB_NONE_TYPE'
                logger.error(f'For {gse}, pysradb produced attribute error with name {attribute_error.name}')
                raise Exception()
            except ValueError as value_error:
                if value_error.args[0] == 'All arrays must be of the same length':
                    event['pysradb_failure_reason'] = 'PYSRADB_ARRAY_LENGTH'
                    logger.error(f'For {gse}, pysradb produced value error with {value_error.args[0]}')
                    raise Exception()
                else:
                    event['pysradb_failure_reason'] = 'UNKNOWN_VALUE_ERROR'
                    logger.error(f'For {gse}, pysradb produced value error with {value_error.args[0]}')
                    raise Exception()