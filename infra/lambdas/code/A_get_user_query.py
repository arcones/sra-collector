import json
import logging

import boto3
from env_params import env_params

sqs = boto3.client('sqs', region_name='eu-central-1')

def handler(event, context):
    try:
        logging.info(f'Received event {event}')

        output_sqs, _ = env_params.params_per_env(context.function_name)

        request_body = json.loads(event['body'])
        ncbi_query = request_body['ncbi_query']

        request_id = event['requestContext']['requestId']
        request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

        sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(request_info))

        logging.info(f'Sent {request_info} message to {output_sqs}')

        return {'statusCode': 201, 'body': json.dumps(request_info), 'headers': {'content-type': 'application/json'}}
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
