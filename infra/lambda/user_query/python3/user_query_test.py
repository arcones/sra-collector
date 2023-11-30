from user_query import handler


def test_user_query():
    assert {
               'statusCode': 200,
               'message': 'The query foo results will be sent to bar'
           } == handler(event={'ncbi_query': 'foo', 'mail': 'bar'}, context=None)
