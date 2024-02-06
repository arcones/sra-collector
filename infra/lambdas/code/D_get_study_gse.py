import json
import logging
import time

import boto3
import urllib3
from env_params import env_params
from postgres_connection import postgres_connection

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()


def handler(event, context):
    try:
        if event:
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
                    _summary_process(context.function_name, study_id, request_info, summary)
                else:
                    logging.warning(f'API Limit reached, retrying')
                    time.sleep(1)
                    continue

                return {'statusCode': 200}
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
        raise e


def _summary_process(function_name: str, study_id: str, request_info: dict, summary: str):
    output_sqs, schema = env_params.params_per_env(function_name)

    logging.debug(f'Study summary from study {study_id} is {summary}')

    gse = _extract_gse_from_summaries(summary)

    if gse:
        logging.info(f'Retrieved gse {gse} for study {study_id}')
        message = {**request_info, 'study_id': study_id, 'gse': gse}
        sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(message))
        logging.info(f'Sent message {message} for study {study_id}')
        _store_gse_in_db(schema, study_id, request_info['request_id'], gse)
    else:
        raise SystemError(f'Unable to fetch gse from {study_id}')


def _extract_gse_from_summaries(summary: str) -> str:
    logging.info(f'Extracting GSE from {summary}')
    if summary['entrytype'] == 'GSE':
        gse = summary['accession']
        logging.info(f'Extracted GSE {gse}')
        return gse
    else:
        message = f'For summary {summary} there are none GSE entrytype'
        logging.error(message)
        raise ValueError(message)


def _store_gse_in_db(schema: str, study_id: str, request_id: str, gse: str):
    database_connection = postgres_connection.get_connection()
    cursor = database_connection.cursor()
    statement = cursor.mogrify(
        f'insert into {schema}.geo_study (ncbi_id, request_id, gse) values (%s, %s, %s)',
        (study_id, request_id, gse)
    )
    logging.debug(f'Executing: {statement}...')
    cursor.execute(statement)
    logging.info(f'Inserted geo study info in database')
    database_connection.commit()
    cursor.close()
    database_connection.close()
