import json
import logging

import boto3
from pysradb import SRAweb

ssm = boto3.client('ssm', region_name='eu-central-1')

def _define_log_level():
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']
    the_logger = logging.getLogger('dlq_get_srp_pysradb_error')
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

            study_id = study_with_missing_srp['study_id']
            gse = study_with_missing_srp['gse']

            try:
                srp = SRAweb().gse_to_srp(gse)['study_accession'][0]
                logger.error(f'For study {study_id} with {gse} the SRP is {srp}, so it was possible to extract it. Investigate how this ended in DLQ')
            except AttributeError as attribute_error:
                logger.error(f'For study {study_id} with {gse}, pysradb produced attribute error with name {attribute_error.name}')
            except ValueError as value_error:
                if value_error.args[0] == 'All arrays must be of the same length':
                    logger.error(f'For study {study_id} with {gse}, pysradb produced value error with {value_error.args[0]}')
                else:
                    logger.error(f'For study {study_id} with {gse}, pysradb produced value error with {value_error.args[0]}')
