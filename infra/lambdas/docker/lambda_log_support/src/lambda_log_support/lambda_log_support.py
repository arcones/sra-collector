import logging

import boto3


def define_log_level():
    ssm = boto3.client('ssm', region_name='eu-central-1')
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']
    logger = logging.getLogger('lambda')
    logging.basicConfig(format='%(levelname)s %(message)s')

    if log_level == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    return logger
