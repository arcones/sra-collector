import json
import logging

import boto3
import urllib3
from db_connection.db_connection import DBConnectionManager
from sqs_helper.sqs_helper import SQSHelper

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()
page_size = 500

QUERY_STUDY_LIMIT = 1000


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

                    ncbi_query = request_body['ncbi_query']
                    request_id = request_body['request_id']

                    study_count = get_study_count(ncbi_query)

                    if study_count < QUERY_STUDY_LIMIT:
                        if is_request_pending_to_be_processed(database_holder, request_id, ncbi_query):
                            store_request_in_db(database_holder, request_id, ncbi_query, study_count)

                            retstart = 0
                            message_bodies = []

                            while retstart <= study_count:
                                if retstart > study_count:
                                    retstart = study_count
                                    continue

                                message_bodies.append({'request_id': request_id, 'retstart': retstart, 'retmax': page_size})

                                retstart = retstart + page_size

                            SQSHelper(sqs, context.function_name).send(message_bodies=message_bodies)
                        else:
                            logging.info(f'The record with request_id {request_id} and NCBI query {ncbi_query} has already been processed')
                    else:
                        logging.info(f'Query has {study_count} studies associated which is above the limit of {QUERY_STUDY_LIMIT} studies so it will not be processed')
                        too_expensive_halt_reason = (f'Queries with more than {QUERY_STUDY_LIMIT} studies cannot be processed as costs are not affordable.'
                                                     f'Check how many studies has your query in https://www.ncbi.nlm.nih.gov/gds/?term={ncbi_query}'
                                                     'Do smaller queries or contact webmaster marta.arcones@gmail.com to see alternatives')

                        too_expensive_user_feedback_message = {'request_id': request_id, 'result': 'FAILURE', 'reason': too_expensive_halt_reason}
                        SQSHelper(sqs, context.function_name, 'H_user_feedback').send(message_body=too_expensive_user_feedback_message)
            except Exception as exception:  # TODO add this in all lambdas with a for as it has no relation with the batch send
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')

        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def get_study_count(ncbi_query: str) -> int:
    try:
        logging.debug(f'Getting study count for keyword {ncbi_query}...')
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax=1'
        response = json.loads(http.request('GET', url).data)
        study_count = response['esearchresult']['count']
        logging.info(f'Done get study count for keyword {ncbi_query}. There are {study_count} studies')
        return int(study_count)
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_study_count.__name__}: {str(exception)}')
        raise exception


def store_request_in_db(database_holder, request_id: str, ncbi_query: str, study_count: int):
    try:
        statement = f'insert into request (id, query, geo_count) values (%s, %s, %s) on conflict do nothing;'
        parameters = (request_id, ncbi_query, study_count)
        database_holder.execute_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_request_in_db.__name__}: {str(exception)}')
        raise exception


def is_request_pending_to_be_processed(database_holder, request_id: str, ncbi_query: str) -> bool:
    try:
        statement = f'select id from request where id=%s and query=%s;'
        parameters = (request_id, ncbi_query)
        return database_holder.execute_read_statement(statement, parameters) is None
    except Exception as exception:
        logging.error(f'An exception has occurred in {is_request_pending_to_be_processed.__name__}: {str(exception)}')
        raise exception
