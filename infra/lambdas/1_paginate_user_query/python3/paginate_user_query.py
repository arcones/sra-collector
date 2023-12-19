import json
import logging
from time import time

import boto3
import urllib3

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/user_query_pages_queue'

sqs = boto3.client('sqs', region_name='eu-central-1')
ssm = boto3.client('ssm', region_name='eu-central-1')

http = urllib3.PoolManager()

page_size = 500


def _define_log_level():
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']
    the_logger = logging.getLogger('paginate_user_query')
    logging.basicConfig(format='%(levelname)s %(message)s')

    if log_level == 'DEBUG':
        the_logger.setLevel(logging.DEBUG)
    else:
        the_logger.setLevel(logging.INFO)

    return the_logger


logger = _define_log_level()


def handler(event, context): ## TODO instead of picking request, pick from SQS
    if event:
        logger.debug(f'Received event {event}')
        for record in event['Records']:
            request_body = json.loads(record['body'])
            ncbi_query = request_body['ncbi_query']
            request_id = request_body['request_id']

            request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

            study_count = _get_study_count(ncbi_query)
            retstart = 0
            message_sent_count = 0

            while retstart <= study_count:
                if retstart > study_count:
                    retstart = study_count
                    continue

                message = json.dumps({**request_info, 'retstart': retstart, 'retmax': page_size})

                sqs.send_message(QueueUrl=output_sqs, MessageBody=message)
                message_sent_count = message_sent_count + 1
                logger.debug(f'Sent {message} message to {output_sqs}')

                retstart = retstart + page_size

            logger.debug(f'Sent {message_sent_count} messages to {output_sqs}')

    ## TODO also add to request table


def _get_study_count(ncbi_query: str) -> int:
    logger.debug(f'Getting study count for keyword {ncbi_query}...')
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax=1'
    response = json.loads(http.request('GET', url).data)
    study_count = response['esearchresult']['count']
    logger.debug(f'Done get study count for keyword {ncbi_query}. There are {study_count} studies')
    return int(study_count)
