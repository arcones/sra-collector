from user_query.user_query import handler


def test_user_query():
    request_body_as_received_by_lambda = {'body': '{\n  "ncbi_query": "stroke AND single cell rna seq AND musculus"\n}'}

    expected_lambda_response = {'statusCode': 200, 'body': '{"study_ids": ["200247102", "200207275", "200189432", "200167593", "200174574", "200126815", "200150644"]}'}
    assert expected_lambda_response == handler(event=request_body_as_received_by_lambda, context=None)
