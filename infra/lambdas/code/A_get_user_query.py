import json
import logging

import boto3
from lambda_log_support import lambda_log_support

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/user_query_queue'
sqs = boto3.client('sqs', region_name='eu-central-1')

def handler(event, context):
    try:
        request_id = event['requestContext']['requestId']
        lambda_log_support.configure_logger(request_id, context.aws_request_id)

        logging.info(f'Received event {event}')

        request_body = json.loads(event['body'])
        ncbi_query = request_body['ncbi_query']

        request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

        sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(request_info))

        logging.info(f'Sent {request_info} message to {output_sqs}')

        return {'statusCode': 201, 'body': json.dumps(request_info), 'headers': {'content-type': 'application/json'}}
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
