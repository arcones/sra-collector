import logging

import boto3

def configure_logger(request_id: str):
    ssm = boto3.client('ssm', region_name='eu-central-1')
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']

    if log_level == 'DEBUG':
        level = logging.DEBUG
    else:
        level = logging.INFO

    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
    logging.basicConfig(format=f'%(levelname)s {request_id} %(message)s', level=level)
