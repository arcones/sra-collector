import json

from python3.user_query.user_query import lambda_handler


def test_user_query():
    assert {
               'statusCode': 200,
               'body': json.dumps({'event': 'foo', 'context': 'bar'})
           } == lambda_handler(event='foo', context='bar')
