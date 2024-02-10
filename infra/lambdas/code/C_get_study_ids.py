import json
import logging
import time

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
            logging.info(f'Received {len(event["Records"])} records event {event}')
            for record in event['Records']:
                request_body = json.loads(record['body'])

                logging.info(f'Processing record {request_body}')

                ncbi_query = request_body['ncbi_query']
                request_id = request_body['request_id']
                retstart = request_body['retstart']
                retmax = request_body['retmax']

                logging.debug(f'Query received for keyword {ncbi_query} with retstart {retstart} and retmax {retmax}')

                study_list = _esearch_entities_list(ncbi_query, retstart, retmax)

                logging.debug(f"Study list contains: {','.join(map(str, sorted(study_list)))}")

                messages = []

                for study_id in study_list:
                    messages.append({
                        'Id': str(time.time()).replace('.', ''),
                        'MessageBody': json.dumps({'request_id': request_id, 'ncbi_query': ncbi_query, 'study_id': study_id})
                    })

                message_batches = [messages[index:index + 10] for index in range(0, len(messages), 10)]

                for message_batch in message_batches:
                    sqs.send_message_batch(QueueUrl=output_sqs, Entries=message_batch)

                logging.info(f'Sent {len(messages)} messages to {output_sqs.split("/")[-1]}')
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
