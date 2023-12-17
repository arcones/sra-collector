import json
import logging

import boto3

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/user_query_queue'

sqs = boto3.client('sqs', region_name='eu-central-1')
ssm = boto3.client('ssm', region_name='eu-central-1')

def _define_log_level():
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']
    the_logger = logging.getLogger('paginate_user_query')
    logging.basicConfig(format='%(levelname)s %(message)s')

    if log_level == 'DEBUG':
        the_logger.setLevel(logging.DEBUG)
    else:
        the_logger.setLevel(logging.INFO)

    return the_logger


logger = _define_log_level()


def handler(event, context):
    logger.debug(f'Received event {event}')
    request_id = event['requestContext']['requestId']
    request_body = json.loads(event['body'])
    ncbi_query = request_body['ncbi_query']

    request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

    sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(request_info))

    logger.debug(f'Sent {request_info} message to {output_sqs}')

    return {'statusCode': 201, 'body': json.dumps(request_info), 'headers': {'content-type': 'application/json'}}
