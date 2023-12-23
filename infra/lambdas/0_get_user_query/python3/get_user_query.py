import json

import boto3
from lambda_log_support import lambda_log_support

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/user_query_queue'

sqs = boto3.client('sqs', region_name='eu-central-1')

logger = lambda_log_support.define_log_level()

def handler(event, context):
    logger.debug(f'Received event {event}')
    request_id = event['requestContext']['requestId']
    request_body = json.loads(event['body'])
    ncbi_query = request_body['ncbi_query']

    request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

    sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(request_info))

    logger.debug(f'Sent {request_info} message to {output_sqs}')

    return {'statusCode': 201, 'body': json.dumps(request_info), 'headers': {'content-type': 'application/json'}}
