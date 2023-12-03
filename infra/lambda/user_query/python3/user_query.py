import json
import logging

import boto3
import urllib3

logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('user_query')
logger.setLevel(logging.INFO)

BATCH_SIZE = 500
http = urllib3.PoolManager()

sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    request_body = json.loads(event['body'])
    ncbi_query = request_body['ncbi_query']
    logger.info(f'Query received for keyword {ncbi_query}')

    study_list = get_study_list(ncbi_query)

    for study in study_list:
        sqs.send_message(
            QueueUrl='https://sqs.eu-centrla-1.amazonaws.com/120715685161/user_query_queue',
            MessageBody=study
        )

    return {
        'statusCode': 200,
        'headers': {'content-type': 'application/json'},
        'body': ''
    }


def get_study_list(search_keyword: str) -> list[int]:
    logger.info(f'Get study list for keyword {search_keyword}...')
    idlist = esearch_study_list(search_keyword)
    logger.info(f'Done get study list for keyword {search_keyword}')
    return idlist


def esearch_study_list(keyword: str) -> list[int]:
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={keyword}'
    logger.debug(f'HTTP GET started ==> {url}')
    response = _paginated_esearch(url)
    logger.debug(f'HTTP GET finished ==> {url}')
    return response


def _paginated_esearch(url: str) -> list[int]:
    retstart = 0
    paginated_url = url + f'&retmax={BATCH_SIZE}&usehistory=y'
    idlist = []
    while True:
        response = json.loads(http.request('GET', f'{paginated_url}&retstart={retstart}').data)
        idlist += response['esearchresult']['idlist']
        if int(response['esearchresult']['retmax']) < BATCH_SIZE:
            return idlist
        else:
            retstart += BATCH_SIZE
