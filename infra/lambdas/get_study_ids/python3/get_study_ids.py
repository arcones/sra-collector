import json
import logging
from time import time

import boto3
import urllib3

logging.basicConfig(format='%(levelname)s %(message)s')
logger = logging.getLogger('get_study_ids')
logger.setLevel(logging.DEBUG)

BATCH_SIZE = 500
http = urllib3.PoolManager()

sqs = boto3.client('sqs', region_name='eu-central-1')

def handler(event, context):
    if event:
        logger.debug(f'Received event {event}')
        for record in event['Records']:
            request_body = json.loads(event['body'])
            query = request_body['query']
            logger.debug(f'Query received for keyword {query}')

            study_list = get_study_list(query)
            request_id = round(time())
            request_info = {'request_id': request_id, 'study_count': len(study_list)}

            for study_id in study_list:
                sqs.send_message(
                    QueueUrl='https://sqs.eu-central-1.amazonaws.com/120715685161/study_ids_queue',
                    MessageBody=json.dumps({
                        'request_info': request_info,
                        'study_id': study_id
                    })
                )

            logger.info(f"Pushed {request_info['study_count']} message/s to study ids queue")


def get_study_list(search_keyword: str) -> list[int]:
    logger.debug(f'Get study list for keyword {search_keyword}...')
    idlist = esearch_study_list(search_keyword)
    logger.debug(f'Done get study list for keyword {search_keyword}')
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
