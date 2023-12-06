import json
import logging

import boto3
import urllib3

logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('user_query')
logger.setLevel(logging.DEBUG)

NCBI_RETRY_MAX = 50

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()


def handler(event, context):
    if event:
        ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key')
        ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

        base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'

        for record in event['Records']:
            study_request = json.loads(record['body'])
            study_id = study_request['study_id']
            logger.info(f'Study request received {study_request}')

            url = f'{base_url}&id={study_id}'
            retries_count = 1
            while retries_count < NCBI_RETRY_MAX:
                response = http.request('GET', url)
                if response.status == 200:
                    summary = json.loads(response.data)
                    logger.debug(f'Study summary from study {study_id} is {summary}')
                    return sqs.send_message(
                        QueueUrl='https://sqs.eu-central-1.amazonaws.com/120715685161/study_summaries_queue',
                        MessageBody=json.dumps({**study_request, 'gse': _extract_gse_from_summaries(study_id, summary)})
                    )
                else:
                    logger.info(f'HTTP GET finished with unexpected code {response.status} in retry #{retries_count} ==> {url}')
                    retries_count += 1
                    logger.info(f'Retries incremented to {retries_count}')
            raise Exception(f'Unable to fetch {study_id} in {NCBI_RETRY_MAX} attempts')


def _extract_gse_from_summaries(study_id, summary) -> str:
    study_summary_payload = summary['result'][study_id]
    logger.debug(f'Extracting GSE from {study_summary_payload}')
    if study_summary_payload['entrytype'] == 'GSE':
        return study_summary_payload['accession']
