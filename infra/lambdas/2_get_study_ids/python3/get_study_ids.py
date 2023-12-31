import json

import boto3
import urllib3
from lambda_log_support import lambda_log_support

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/study_ids_queue'

STUDY_ID_MIN = 200000000
STUDY_ID_MAX = 299999999

sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()

logger = lambda_log_support.define_log_level()

def handler(event, context):
    if event:
        logger.debug(f'Received event {event}')
        for record in event['Records']:
            request_body = json.loads(record['body'])

            ncbi_query = request_body['ncbi_query']
            request_id = request_body['request_id']
            retstart = request_body['retstart']
            retmax = request_body['retmax']

            logger.debug(f'Query received for keyword {ncbi_query} with retstart {retstart} and retmax {retmax}')

            entities_list = _esearch_entities_list(ncbi_query, retstart, retmax)

            study_list = [study for study in entities_list if STUDY_ID_MIN <= study < STUDY_ID_MAX]

            logger.debug(f'From {len(entities_list)} entities, {len(study_list)} studies were extracted')

            logger.debug(f"Study list contains: {','.join(map(str,sorted(study_list)))}")

            request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

            for study_id in study_list:
                message = json.dumps({'request_info': request_info, 'study_id': study_id})

                sqs.send_message(QueueUrl=output_sqs, MessageBody=message)

            logger.debug(f'Sent {len(study_list)} messages to {output_sqs}')

            return {'statusCode': 200}


def _esearch_entities_list(ncbi_query: str, retstart: int, retmax: int) -> list[int]:
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax={retmax}&retstart={retstart}&usehistory=y'
    logger.debug(f'Get entity list for keyword {ncbi_query}...')
    response = json.loads(http.request('GET', url).data)
    logger.debug(f'Done get entity list for keyword {ncbi_query}')
    entities_list = response['esearchresult']['idlist']
    logger.debug(f"Entity list contains: {','.join(entities_list)}")
    return list(map(int, entities_list))
