import json
import time

import boto3
import urllib3
from lambda_log_support import lambda_log_support

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/gses_queue'

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()

logger = lambda_log_support.define_log_level()


def handler(event, context):
    if event:
        logger.debug(f'Received event {event}')
        ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key_secret')
        ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

        base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'

        for record in event['Records']:
            study_request = json.loads(record['body'])
            study_id = str(study_request['study_id'])
            request_info = study_request['request_info']

            url = f'{base_url}&id={study_id}'
            logger.debug(f'The URL is {url}')
            response_status = 0

            while response_status != 200:
                response = http.request('GET', url)
                response_status = response.status
                if response_status == 200:
                    logger.debug(f'The response is {response.data}')
                    summary = json.loads(response.data)['result'][study_id]
                    _summary_process(study_id, request_info, summary)
                else:
                    logger.debug(f'API Limit reached, retrying')
                    time.sleep(1)
                    continue

            return {'statusCode': 200}


def _summary_process(study_id: str, request_info: dict, summary: str):
    logger.debug(f'Study summary from study {study_id} is {summary}')
    gse = _extract_gse_from_summaries(summary)

    if gse:
        logger.debug(f'Retrieved gse {gse} for study {study_id}')
        message = {**request_info, 'study_id': study_id, 'gse': gse}
        sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(message))
        logger.debug(f'Sent message {message} for study {study_id}')
    else:
        raise Exception(f'Unable to fetch gse from {study_id}')


def _extract_gse_from_summaries(summary: str) -> str:
    logger.debug(f'Extracting GSE from {summary}')
    if summary['entrytype'] == 'GSE':
        gse = summary['accession']
        logger.debug(f'Extracted GSE {gse}')
        return gse
    else:
        logger.error(f'For summary {summary} there are none GSE entrytype')
