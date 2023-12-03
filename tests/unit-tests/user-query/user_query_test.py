import sys

from user_query import handler

sys.path.append('infra/lambda/user-query/python3')

S_QUERY = 'stroke AND single cell rna seq AND musculus'


def test_user_query():
    request_body_as_received_by_lambda = {'body': '{\n  "ncbi_query": "' + S_QUERY + '"\n}'}
    expected_lambda_response = {'statusCode': 200, 'headers': {'content-type': 'application/json'}, 'body': ''}

    assert expected_lambda_response == handler(event=request_body_as_received_by_lambda, context=None)
