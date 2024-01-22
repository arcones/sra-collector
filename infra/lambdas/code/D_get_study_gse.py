import json
import logging
import time

import boto3
import urllib3
from postgres_connection import postgres_connection
# from lambda_log_support import lambda_log_support

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/gses_queue'

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()


def handler(event, context):
    try:
        if event:
            request_id = json.loads(event['Records'][0]['body'])['request_info']['request_id']
            # lambda_log_support.configure_logger(request_id, context.aws_request_id)
            logging.info(f'Received event {event}')

            ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key_secret')
            ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

            base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'

            for record in event['Records']:
                study_request = json.loads(record['body'])
                study_id = str(study_request['study_id'])
                request_info = study_request['request_info']

                url = f'{base_url}&id={study_id}'
                logging.debug(f'The URL is {url}')
                response_status = 0

                while response_status != 200:
                    response = http.request('GET', url)
                    response_status = response.status
                    if response_status == 200:
                        logging.debug(f'The response is {response.data}')
                        summary = json.loads(response.data)['result'][study_id]
                        _summary_process(study_id, request_info, summary)
                    else:
                        logging.warning(f'API Limit reached, retrying')
                        time.sleep(1)
                        continue

                return {'statusCode': 200}
    except:
        logging.exception(f'An exception has occurred')


def _summary_process(study_id: str, request_info: dict, summary: str):
    try:
        logging.debug(f'Study summary from study {study_id} is {summary}')
        gse = _extract_gse_from_summaries(summary)

        if gse:
            logging.info(f'Retrieved gse {gse} for study {study_id}')
            message = {**request_info, 'study_id': study_id, 'gse': gse}
            sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(message))
            logging.info(f'Sent message {message} for study {study_id}')
            _store_gse_in_db(study_id, request_info['request_id'], gse)
        else:
            raise Exception(f'Unable to fetch gse from {study_id}')
    except:
        logging.exception(f'An exception has occurred')


def _extract_gse_from_summaries(summary: str) -> str:
    try:
        logging.info(f'Extracting GSE from {summary}')
        if summary['entrytype'] == 'GSE':
            gse = summary['accession']
            logging.info(f'Extracted GSE {gse}')
            return gse
        else:
            logging.error(f'For summary {summary} there are none GSE entrytype')
    except:
        logging.exception(f'An exception has occurred')

def _store_gse_in_db(study_id: str, request_id: str, gse: str):
    try:
        database_connection = postgres_connection.get_connection()
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            'insert into geo_study (ncbi_id, request_id, gse) values (%s, %s, %s)',
            (study_id, request_id, gse)
        )
        logging.debug(f'Executing: {statement}...')
        cursor.execute(statement)
        logging.info(f'Inserted geo study info in database')
        database_connection.commit()
        cursor.close()
        database_connection.close()
    except:
        logging.exception(f'An exception has occurred')
