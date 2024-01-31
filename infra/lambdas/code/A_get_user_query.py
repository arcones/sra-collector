import json
import logging
import os

import boto3

sqs = boto3.client('sqs', region_name='eu-central-1')


def _select_proper_queue_per_env() -> str:
    output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/integration_test_queue'
    if os.environ['ENV'] == 'prod':
        output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/user_query_queue'
    logging.debug(f'Queue in use is {output_sqs}')
    return output_sqs


def handler(event, context):
    try:
        logging.info(f'Received event {event}')

        output_sqs = _select_proper_queue_per_env()

        request_body = json.loads(event['body'])
        ncbi_query = request_body['ncbi_query']

        request_id = event['requestContext']['requestId']
        request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

        sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(request_info))

        logging.info(f'Sent {request_info} message to {output_sqs}')

        return {'statusCode': 201, 'body': json.dumps(request_info), 'headers': {'content-type': 'application/json'}}
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
