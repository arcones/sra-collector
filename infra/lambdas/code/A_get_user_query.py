import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from sqs_helper.sqs_helper import SQSHelper

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

cognito = boto3.client('cognito-idp', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    try:
        logging.info(f'Received event {event}')

        username = event['headers']['username']
        password = event['headers']['password']

        if authenticate_user(username, password):
            request_id = event['requestContext']['requestId']

            request_body = json.loads(event['body'])

            ncbi_query = request_body['ncbi_query']

            message_body = {'request_id': request_id, 'ncbi_query': ncbi_query}

            SQSHelper(sqs, context.function_name).send(message_body={**message_body, 'mail': username})

            return {'statusCode': 201, 'body': json.dumps(message_body), 'headers': {'content-type': 'application/json'}}
        else:
            return {'statusCode': 401}
    except Exception as exception:
        logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')
        raise exception


def authenticate_user(username: str, password: str) -> bool:
    try:
        authentication = cognito.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            ClientId=os.environ.get('COGNITO_CLIENT_ID'),
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'USERPOOL_ID': os.environ.get('COGNITO_POOL_ID')
            }
        )
        if authentication['AuthenticationResult']:
            return True
    except ClientError as client_error: #TODO aquimequede no consigo autenticarme
        logging.warning(f'Bad credentials provided {authenticate_user.__name__}: {str(client_error)}')
        return False
