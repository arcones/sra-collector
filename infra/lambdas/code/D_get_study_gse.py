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
                study_id = request_body['study_id']

                url = f'{base_url}&id={study_id}'
                logging.debug(f'The URL is {url}')
                response_status = 0

                base_delay = 1
                attempts = 0

                while response_status != 200:
                    response = http.request('GET', url)
                    response_status = response.status
                    if response_status == 200:
                        logging.debug(f'The response in attempt #{attempts} is {response.data}')
                        summary = json.loads(response.data)['result'][f'{study_id}']
                        _summary_process(context.function_name, request_body, summary)
                    else:
                        exponential_backoff = base_delay * (2 ** attempts) + random.uniform(0, 0.1)
                        logging.debug(f'API Limit reached in attempt #{attempts}, retrying in {round(exponential_backoff,2)} seconds')
                        time.sleep(exponential_backoff)
                        continue
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _summary_process(function_name: str, request_body: dict, summary: str):
    try:
        output_sqs, schema = env_params.params_per_env(function_name)
        logging.debug(f"Study summary from study {request_body['study_id']} is {summary}")
        geo_entity = _extract_geo_entity_from_summaries(summary)

        if geo_entity.startswith('GSE'):
            logging.info(f"Retrieved gse {geo_entity} for study {request_body['study_id']}")
            message = {**request_body, 'gse': geo_entity}
            _store_gse_in_db(schema, request_body['request_id'], request_body['study_id'], geo_entity)
            sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(message))
            logging.info(f"Sent message {message} for study {request_body['study_id']}")
        elif geo_entity.startswith('GSM'):
            logging.info(f"Retrieved gsm {geo_entity} for study {request_body['study_id']}")
            _store_gsm_in_db(schema, request_body['request_id'], request_body['study_id'], geo_entity)
        else:
            raise SystemError(f"Unable to fetch gse from {request_body['study_id']}")
    except Exception as exception:
        if exception is not SystemError:
            logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _extract_geo_entity_from_summaries(summary: str) -> str:
    try:
        logging.info(f'Extracting GSE from {summary}')
        if summary['entrytype'] == 'GSE' or summary['entrytype'] == 'GSM':
            geo_entity = summary['accession']
            logging.info(f'Extracted GEO entity {geo_entity}')
            return geo_entity
        else:
            message = f'For summary {summary} there are none GEO entity'
            logging.error(message)
            raise ValueError(message)
    except Exception as exception:
        if exception is not ValueError:
            logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _store_gse_in_db(schema: str, request_id: str, study_id: int, gse: str):
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


def _store_gsm_in_db(schema: str, request_id: str, study_id: int, gsm: str):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(
            f'insert into {schema}.geo_experiment (ncbi_id, request_id, gsm) values (%s, %s, %s)',
            (study_id, request_id, gsm)
        )
        postgres_connection.execute_write_statement(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
