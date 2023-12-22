import logging
import os

import boto3

ssm = boto3.client('ssm', region_name='eu-central-1')

def define_log_level(lambda_name: str):
    filename = os.path.basename(__file__)
    log_level = ssm.get_parameter(Name=lambda_name)['Parameter']['Value']
    the_logger = logging.getLogger(filename)
    logging.basicConfig(format='%(levelname)s %(message)s')

    if log_level == 'DEBUG':
        the_logger.setLevel(logging.DEBUG)
    else:
        the_logger.setLevel(logging.INFO)

    return the_logger
