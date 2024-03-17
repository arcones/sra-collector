import json
import logging
import os

import boto3


boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')

if os.environ['ENV'] == 'prod':
    output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/A_user_query'
else:
    output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/integration_test_queue'


def handler(event, context):
    try:
        logging.info(f'Received event {event}')

        request_body = json.loads(event['body'])
        ncbi_query = request_body['ncbi_query']

        request_id = event['requestContext']['requestId']
        request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

        sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(request_info))

        logging.info(f'Sent {request_info} message to {output_sqs}')

        return {'statusCode': 201, 'body': json.dumps(request_info), 'headers': {'content-type': 'application/json'}}
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
