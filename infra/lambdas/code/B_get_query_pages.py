import json
import logging
import time

import boto3
import urllib3
from env_params import env_params
from postgres_connection import postgres_connection

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')
http = urllib3.PoolManager()
page_size = 500


def handler(event, context):
    output_sqs, schema = env_params.params_per_env(context.function_name)

    if event:

        logging.info(f'Received {len(event["Records"])} records event {event}')

        batch_item_failures = []
        sqs_batch_response = {}

        for record in event['Records']:
            try:
                request_body = json.loads(record['body'])

                logging.info(f'Processing record {request_body}')

                ncbi_query = request_body['ncbi_query']
                request_id = request_body['request_id']

                request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

                study_count = _get_study_count(ncbi_query)

                if _is_request_pending_to_be_processed(schema, request_id, ncbi_query, study_count):
                    _store_request_in_db(schema, request_id, ncbi_query, study_count)

                    retstart = 0
                    messages = []

                    while retstart <= study_count:
                        if retstart > study_count:
                            retstart = study_count
                            continue

                        messages.append({
                            'Id': str(time.time()).replace('.', ''),
                            'MessageBody': json.dumps({**request_info, 'retstart': retstart, 'retmax': page_size})
                        })

                        retstart = retstart + page_size

                    message_batches = [messages[index:index + 10] for index in range(0, len(messages), 10)]

                    for message_batch in message_batches:
                        sqs.send_message_batch(QueueUrl=output_sqs, Entries=message_batch)

                    logging.info(f'Sent {len(messages)} messages to {output_sqs.split("/")[-1]}')
                else:
                    logging.info(f'The record with request_id {request_id} and NCBI query {ncbi_query} has already been processed')
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred: {str(exception)}')
        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def _get_study_count(ncbi_query: str) -> int:
    try:
        logging.debug(f'Getting study count for keyword {ncbi_query}...')
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax=1'
        response = json.loads(http.request('GET', url).data)
        study_count = response['esearchresult']['count']
        logging.info(f'Done get study count for keyword {ncbi_query}. There are {study_count} studies')
        return int(study_count)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _store_request_in_db(schema: str, request_id: str, ncbi_query: str, study_count: int):
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(
            f'insert into {schema}.request (id, query, geo_count) values (%s, %s, %s);',
            (request_id, ncbi_query, study_count)
        )
        postgres_connection.execute_write_statement(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _is_request_pending_to_be_processed(schema: str, request_id: str, ncbi_query: str, study_count: int) -> bool:
    try:
        database_connection, database_cursor = postgres_connection.get_database_holder()
        statement = database_cursor.mogrify(
            f'select id from {schema}.request where id=%s and query=%s and geo_count=%s',
            (request_id, ncbi_query, study_count)
        )
        return not postgres_connection.is_row_present(database_connection, database_cursor, statement)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
