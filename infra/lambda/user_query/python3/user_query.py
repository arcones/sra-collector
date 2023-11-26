def handler(event, context):
    message = 'The query {} results will be sent to {}'.format(event['ncbi_query'], event['mail'])
    return {
        'statusCode': 200,
        'message': message
    }
