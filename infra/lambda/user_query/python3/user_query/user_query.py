import json


def handler(event, context):
    request_body = json.loads(event['body'])
    message = 'The query {} results will be sent to {}'.format(request_body['ncbi_query'], request_body['mail'])
    return {
        'statusCode': 200,
        'message': message
    }
