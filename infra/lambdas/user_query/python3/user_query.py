import json
import logging
from time import time

import boto3
import urllib3

logging.basicConfig(format='%(levelname)s %(message)s')
logger = logging.getLogger('user_query')
logger.setLevel(logging.DEBUG)

sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    logger.debug(f'Received event {event}')
    request_body = json.loads(event['body'])
    logger.debug(f'Query received for keyword {request_body}')

    response = json.dumps({
        'request_info': {'request_id': round(time())},
        'query': request_body['ncbi_query']
    })

    sqs.send_message(
        QueueUrl='https://sqs.eu-central-1.amazonaws.com/120715685161/user_query_queue',
        MessageBody=response
    )

    return {
        'statusCode': 201,
        'body': response,
        'headers': {'content-type': 'application/json'}
    }
