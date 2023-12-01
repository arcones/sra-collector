from user_query.user_query import handler


def test_user_query():
    request_body_as_received_by_lambda = {'body': '{\n  "ncbi_query": "foo",\n  "mail": "bar"\n}'}

    expected_lambda_response = {'statusCode': 200, 'body': 'The query foo results will be sent to bar'}

    assert expected_lambda_response == handler(event=request_body_as_received_by_lambda, context=None)
