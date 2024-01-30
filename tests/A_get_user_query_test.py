import json

import boto3
import botocore

LAMBDA_TIMEOUT = 90

botocore_client = botocore.client.Config(signature_version=botocore.UNSIGNED, read_timeout=LAMBDA_TIMEOUT, retries={'max_attempts': 0})

lambda_client = boto3.client('lambda', region_name='eu-central-1', endpoint_url='http://localhost:3001', use_ssl=False, verify=False, config=botocore_client)


def test_validate_lambda_response():
    with open('tests/lambdas-input/A_get_user_query_input.json') as json_data:
        payload = json.load(json_data)
        response = lambda_client.invoke(
            FunctionName='A_get_user_query',
            Payload=json.dumps(payload))

    actual_response = json.loads(response['Payload'].read())

    actual_response_status = actual_response['statusCode']
    actual_response_payload = actual_response['body']

    assert actual_response_status == 201
    assert actual_response_payload == '{"request_id": "ST9QVi5rliAEJgg=", "ncbi_query": "integration tests"}'
