def lambda_handler(event, context):
    message = 'NCBI GEO datasets query "{}" will processed. A mail to "{}" will be sent when results are ready'.format(event['ncbi_query'], event['mail'])  
    return { 
        'message' : message
    }