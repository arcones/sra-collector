import inspect
import json
import logging

import boto3
from sqs_helper.sqs_helper import SQSHelper

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    try:
        logging.info(f'Received event {event}')

        request_body = json.loads(event['body'])
        ncbi_query = request_body['ncbi_query']

        request_id = event['requestContext']['requestId']
        request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

        SQSHelper(context.function_name, sqs).send(message_body=request_info)

        return {'statusCode': 201, 'body': json.dumps(request_info), 'headers': {'content-type': 'application/json'}}
    except Exception as exception:
        logging.error(f'An exception has occurred in {handler.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception
