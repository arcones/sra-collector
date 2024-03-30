import json
import random
import string


def provide_random_request_id():
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(20))


def sqs_wrap(bodies: [str], dumps: bool = False) -> dict:
    sqs_message_without_body = {
        'messageId': 'fe1e0334-c5c1-4e76-975a-832c16dd4c1c',
        'receiptHandle': 'AQEB503JmCqXJ6XSLNL+M7tdFRPpON7z6JPhiYOy+fNv3iN22QHAGFasCcajuIjOq3s5/6lDIBnoE6cFPeRc7A3yT/rmqkehpnkxFIYqGOwXeOnM0FoKDd39aNiybjAD7ADL1kW9jpqu4PaiDVQKCI0+v3McJVfdGayROAXGFcgAcO9BX5HbyevJpKU9C+pVQCwcDmXVawP53TuZeWjVwOLG+SgdqGpNCKYD4kjOIC060bsSek3MoMrKQx+huXSvz+Nrs6OQa4fdJ9c/M3zb9sbaIaYd5d2GMTegQZPgxyEHdLdoI1v9eGqDvIP21kQD4Q8y/Xf1vT4PIXTkgHV1f5m1ccn5wXO8XyAvzc6/BdgL8r4lAYLDYFTYMpnH+35Qs2hwXP3jh8SbcfzFNUEV22rjDw==',
        'attributes': {
            'ApproximateReceiveCount': '1',
            'AWSTraceHeader': 'Root=1-65be78eb-7a59c90254665fce0b0fc5aa;Parent=3856816849320e54;Sampled=0;Lineage=2dfc983d:0',
            'SentTimestamp': '1706981613100',
            'SenderId': 'AROARYGZXFUU2YMSEOV67:foo_bar',
            'ApproximateFirstReceiveTimestamp': '1706981613105'
        },
        'messageAttributes': {},
        'md5OfBody': 'b8852234cf7aad8b1086dd58a47a616b',
        'eventSource': 'aws:sqs',
        'eventSourceARN': 'arn:aws:sqs:eu-central-1:120715685161:kilombo',
        'awsRegion': 'eu-central-1'
    }

    sqs_records = {'Records': [{**sqs_message_without_body, 'body': body} for body in bodies]}

    if dumps:
        sqs_records = json.dumps(sqs_records)

    return sqs_records


def _apigateway_wrap(request_id: str, body: dict, dumps: bool = False) -> dict:
    payload = json.dumps(body)

    with open(f'tests/fixtures/A_get_user_query_input.json') as json_data:
        input_body = json.load(json_data)
        input_body['requestContext']['requestId'] = request_id
        input_body['body'] = payload

    if dumps:
        input_body = json.dumps(input_body)

    return input_body
