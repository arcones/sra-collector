import json
import logging

import boto3
import urllib3
from env_params import env_params

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

STUDY_ID_MIN = 200000000
STUDY_ID_MAX = 299999999

sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()


def handler(event, context):
    try:
        output_sqs, _ = env_params.params_per_env(context.function_name)
        if event:
            for record in event['Records']:
                request_body = json.loads(record['body'])

                logging.info(f'Received event {request_body}')

                ncbi_query = request_body['ncbi_query']
                request_id = request_body['request_id']
                retstart = request_body['retstart']
                retmax = request_body['retmax']

                logging.debug(f'Query received for keyword {ncbi_query} with retstart {retstart} and retmax {retmax}')

                entities_list = _esearch_entities_list(ncbi_query, retstart, retmax)

                study_list = [study for study in entities_list if STUDY_ID_MIN <= study < STUDY_ID_MAX]

                logging.info(f'From {len(entities_list)} entities, {len(study_list)} studies were extracted')

                logging.debug(f"Study list contains: {','.join(map(str, sorted(study_list)))}")

                request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

                for study_id in study_list:
                    message = json.dumps({'request_info': request_info, 'study_id': study_id})

                    sqs.send_message(QueueUrl=output_sqs, MessageBody=message)

                logging.info(f'Sent {len(study_list)} messages to {output_sqs}')

                return {'statusCode': 200}
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _esearch_entities_list(ncbi_query: str, retstart: int, retmax: int) -> list[int]:
    try:
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax={retmax}&retstart={retstart}&usehistory=y'
        logging.info(f'Get entity list for keyword {ncbi_query}...')
        response = json.loads(http.request('GET', url).data)
        logging.info(f'Done get entity list for keyword {ncbi_query}')
        entities_list = response['esearchresult']['idlist']
        logging.info(f"Entity list contains: {','.join(entities_list)}")
        return list(map(int, entities_list))
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
