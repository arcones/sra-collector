import json
import logging

import boto3
import urllib3

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/study_ids_queue'

sqs = boto3.client('sqs', region_name='eu-central-1')
ssm = boto3.client('ssm', region_name='eu-central-1')
lambda_function = boto3.client('lambda', region_name='eu-central-1')

http = urllib3.PoolManager()


def _define_log_level():
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']
    the_logger = logging.getLogger('user_query')
    logging.basicConfig(format='%(levelname)s %(message)s')

    if log_level == 'DEBUG':
        the_logger.setLevel(logging.DEBUG)
    else:
        the_logger.setLevel(logging.INFO)

    return the_logger


logger = _define_log_level()


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

            study_list = _esearch_study_list(ncbi_query, retstart, retmax)

            request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

            for study_id in study_list:
                message = json.dumps({'request_info': request_info, 'study_id': study_id})

                sqs.send_message(QueueUrl=output_sqs, MessageBody=message)

            logger.debug(f'Sent {len(study_list)} messages to {output_sqs}')

            return {'statusCode': 200}


def _esearch_study_list(ncbi_query: str, retstart: int, retmax: int) -> list[int]:
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax={retmax}&retstart={retstart}&usehistory=y'
    logger.debug(f'Get study list for keyword {ncbi_query}...')
    response = json.loads(http.request('GET', url).data)
    logger.debug(f'Done get study list for keyword {ncbi_query}')
    idlist = response['esearchresult']['idlist']
    logger.debug(f'Idlist contains {len(idlist)} studies')
    return idlist
