import json
import logging

import urllib3

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(filename)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
BATCH_SIZE = 500
http = urllib3.PoolManager()


def handler(event, context):
    request_body = json.loads(event['body'])
    ncbi_query = request_body['ncbi_query']
    logging.info(f'Query received for keyword {ncbi_query}')

    study_list = get_study_list(ncbi_query)

    return {
        'statusCode': 200,
        'body': json.dumps(study_list)
    }


def get_study_list(search_keyword: str) -> list[int]:
    logging.info(f'Get study list for keyword {search_keyword}...')
    idlist = esearch_study_list(search_keyword)
    logging.info(f'Done get study list for keyword {search_keyword}')
    return idlist


def esearch_study_list(keyword: str) -> list[int]:
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={keyword}'
    logging.debug(f'HTTP GET started ==> {url}')
    response = _paginated_esearch(url)
    logging.debug(f'HTTP GET finished ==> {url}')
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
