import json
import logging
import time

import boto3
import urllib3
from postgres_connection import postgres_connection

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')
output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/C_study_ids'

http = urllib3.PoolManager()


def handler(event, context):
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
                retstart = request_body['retstart']
                retmax = request_body['retmax']

                logging.debug(f'Query received for keyword {ncbi_query} with retstart {retstart} and retmax {retmax}')

                study_list = esearch_entities_list(ncbi_query, retstart, retmax)

                store_study_ids_in_db(request_id, study_list)

                logging.debug(f"Study list contains: {','.join(map(str, sorted(study_list)))}")

                messages = []

                for study_id in study_list:
                    messages.append({
                        'Id': str(time.time()).replace('.', ''),
                        'MessageBody': json.dumps({'request_id': request_id, 'study_id': study_id}) ## TODO hace falta seguir enviando el request_id aqui?
                    })

                message_batches = [messages[index:index + 10] for index in range(0, len(messages), 10)]

                for message_batch in message_batches:
                    sqs.send_message_batch(QueueUrl=output_sqs, Entries=message_batch)

                logging.info(f'Sent {len(messages)} messages to {output_sqs.split("/")[-1]}')
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred: {str(exception)}')
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
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def store_study_ids_in_db(request_id: str, ncbi_ids: [int]):
    try:
        statement = f'insert into ncbi_study (request_id, ncbi_id) values (%s, %s) on conflict (request_id, ncbi_id) do nothing;'
        parameters = [(request_id, ncbi_id) for ncbi_id in ncbi_ids]
        postgres_connection.execute_bulk_write_statement_2(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
