import json
import logging
import random
import time

import boto3
import urllib3
from env_params import env_params
from postgres_connection import postgres_connection

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()


def handler(event, context):
    try:
        if event:
            logging.info(f'Received {len(event["Records"])} records event {event}')
            ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key_secret')
            ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

            base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'

            for record in event['Records']:
                request_body = json.loads(record['body'])

                logging.info(f'Processing record {request_body}')
                study_id = str(request_body['study_id'])
                request_info = request_body['request_info']

                url = f'{base_url}&id={study_id}'
                logging.debug(f'The URL is {url}')
                response_status = 0

                base_delay = 1
                attempts = 0

                while response_status != 200:
                    response = http.request('GET', url)
                    response_status = response.status
                    if response_status == 200:
                        logging.debug(f'The response is {response.data}')
                        summary = json.loads(response.data)['result'][study_id]
                        _summary_process(context.function_name, study_id, request_info, summary)
                    else:
                        exponential_backoff = base_delay * (2 ** attempts) + random.uniform(0, 0.1)
                        logging.debug(f'API Limit reached, retrying in {round(exponential_backoff,2)} seconds')
                        time.sleep(exponential_backoff)
                        continue

    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _summary_process(function_name: str, study_id: str, request_info: dict, summary: str):
    try:
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
    except Exception as exception:
        if exception is not SystemError:
            logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _extract_gse_from_summaries(summary: str) -> str:
    try:
        logging.info(f'Extracting GSE from {summary}')
        if summary['entrytype'] == 'GSE':
            gse = summary['accession']
            logging.info(f'Extracted GSE {gse}')
            return gse
        else:
            message = f'For summary {summary} there are none GSE entrytype'
            logging.error(message)
            raise ValueError(message)
    except Exception as exception:
        if exception is not ValueError:
            logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _store_gse_in_db(schema: str, study_id: str, request_id: str, gse: str):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(
            f'insert into {schema}.geo_study (ncbi_id, request_id, gse) values (%s, %s, %s)',
            (study_id, request_id, gse)
        )
        postgres_connection.execute_write_statement(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception

## TODO missing here to store valueerror and systemerror
## TODO batch send here
