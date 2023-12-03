import urllib3

ENDPOINT = 'https://hxtfx8byeb.execute-api.eu-central-1.amazonaws.com/user_query_lambda_stage/query-study-hierarchy'
http = urllib3.PoolManager()

S_QUERY = 'stroke AND single cell rna seq AND musculus'

def test_xs_request():
    request_body = {'ncbi_query': S_QUERY}
    response = http.request('GET', ENDPOINT, request_body)
    assert {'statusCode': 200} == response.data
