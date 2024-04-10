import json
import logging

import boto3
import urllib3
from db_connection.db_connection import DBConnectionManager
from sqs_helper.sqs_helper import SQSHelper

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()


def handler(event, context):
    if event:
        logging.info(f'Received {len(event["Records"])} records event {event}')

        batch_item_failures = []
        sqs_batch_response = {}

        for record in event['Records']:
            try:
                with DBConnectionManager() as database_holder:
                    request_body = json.loads(record['body'])

                    logging.info(f'Processing record {request_body}')

                    request_id = request_body['request_id']
                    retstart = request_body['retstart']
                    retmax = request_body['retmax']

                    query = get_query(database_holder, request_id)

                    logging.debug(f'Query received for keyword {query} with retstart {retstart} and retmax {retmax}')

                    study_list = esearch_entities_list(query, retstart, retmax)

                    ncbi_study_id_list = store_study_ids_in_db(database_holder, request_id, study_list)

                    message_bodies = [{'ncbi_study_id': ncbi_study_id} for ncbi_study_id in ncbi_study_id_list]

                    SQSHelper(sqs, context.function_name).send(message_bodies=message_bodies)
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')
        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def esearch_entities_list(ncbi_query: str, retstart: int, retmax: int) -> list[int]:
    try:
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax={retmax}&retstart={retstart}&usehistory=y'
        logging.info(f'Get entity list for keyword {ncbi_query}...')
        response = json.loads(http.request('GET', url).data)
        logging.info(f'Done get entity list for keyword {ncbi_query}')
        entities_list = response['esearchresult']['idlist']
        logging.info(f"Entity list contains: {','.join(entities_list)}")
        return list(map(int, entities_list))
    except Exception as exception:
        logging.error(f'An exception has occurred in {esearch_entities_list.__name__}: {str(exception)}')
        raise exception


def store_study_ids_in_db(database_holder, request_id: str, ncbi_ids: [int]):
    try:
        statement = 'insert into ncbi_study (request_id, ncbi_id) values (%s, %s) on conflict do nothing returning id;'
        parameters = [(request_id, ncbi_id) for ncbi_id in ncbi_ids]
        return database_holder.execute_bulk_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_study_ids_in_db.__name__}: {str(exception)}')
        raise exception


def get_query(database_holder, request_id: str):
    try:
        statement = 'select query from request where id=%s;'
        return database_holder.execute_read_statement(statement, (request_id,))[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_query.__name__}: {str(exception)}')
        raise exception
