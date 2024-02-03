import json
import logging

import boto3
import urllib3
from postgres_connection import postgres_connection

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/user_query_pages_queue'

sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()

page_size = 500


def handler(event, context):
    try:
        if event:
            logging.info(f'Received event {event}')
            request_id = json.loads(event['Records'][0]['body'])['request_id']

            for record in event['Records']:
                request_body = json.loads(record['body'])
                ncbi_query = request_body['ncbi_query']

                request_info = {'request_id': request_id, 'ncbi_query': ncbi_query}

                study_count = _get_study_count(ncbi_query)

                _store_request_in_db(request_id, ncbi_query, study_count)

                retstart = 0
                message_sent_count = 0

                while retstart <= study_count:
                    if retstart > study_count:
                        retstart = study_count
                        continue

                    message = json.dumps({**request_info, 'retstart': retstart, 'retmax': page_size})

                    sqs.send_message(QueueUrl=output_sqs, MessageBody=message)
                    message_sent_count = message_sent_count + 1
                    logging.info(f'Sent {message} message to {output_sqs}')

                    retstart = retstart + page_size

                logging.info(f'Sent {message_sent_count} messages to {output_sqs}')
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')


def _get_study_count(ncbi_query: str) -> int:
    try:
        logging.debug(f'Getting study count for keyword {ncbi_query}...')
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&retmode=json&term={ncbi_query}&retmax=1'
        response = json.loads(http.request('GET', url).data)
        study_count = response['esearchresult']['count']
        logging.info(f'Done get study count for keyword {ncbi_query}. There are {study_count} studies')
        return int(study_count)
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')


def _store_request_in_db(request_id: str, ncbi_query: str, study_count: int):
    try:
        database_connection = postgres_connection.get_connection()
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            'insert into request (id, query, geo_count) values (%s, %s, %s)',
            (request_id, ncbi_query, study_count)
        )
        logging.debug(f'Executing: {statement}...')
        cursor.execute(statement)
        logging.info(f'Inserted request info in database')
        database_connection.commit()
        cursor.close()
        database_connection.close()
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
