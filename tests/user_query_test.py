import urllib3

ENDPOINT = 'https://hxtfx8byeb.execute-api.eu-central-1.amazonaws.com/user_query_lambda_stage/query-study-hierarchy'
http = urllib3.PoolManager()


def test_xs_request():
    request_body = {
        'ncbi_query': 'stroke AND single cell rna seq AND musculus'
    }
    response = http.request('GET', ENDPOINT, request_body)
    assert {'statusCode': 200} == response.data
