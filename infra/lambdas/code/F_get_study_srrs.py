import json
import logging
import time
from enum import Enum

import boto3
from db_connection.db_connection import DBConnectionManager
from pysradb import SRAweb

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')
output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/F_srrs'


class PysradbError(Enum):
    TYPE_ERROR = 'TYPE_ERROR'
    ATTRIBUTE_ERROR = 'ATTRIBUTE_ERROR'
    NOT_FOUND = 'NOT_FOUND'


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

                    sra_project_id = request_body['sra_project_id']

                    try:
                        srp = get_srp_sra_project(database_holder, sra_project_id)
                        raw_pysradb_data_frame = SRAweb().srp_to_srr(srp)
                        srrs = list(raw_pysradb_data_frame['run_accession'])
                        srrs = [srr for srr in srrs if srr.startswith('SRR')]

                        if srrs:
                            logging.info(f'For {srp}, SRRs are {srrs}')

                            messages = []

                            for srr in srrs:
                                messages.append({
                                    'Id': str(time.time()).replace('.', ''),
                                    'MessageBody': json.dumps({'srr': srr})
                                })

                            store_srrs_in_db(database_holder, srrs, sra_project_id)

                            message_batches = [messages[index:index + 10] for index in range(0, len(messages), 10)]
                            for message_batch in message_batches:
                                sqs.send_message_batch(QueueUrl=output_sqs, Entries=message_batch)

                            logging.info(f'Sent {len(messages)} messages to {output_sqs.split("/")[-1]}')
                        else:
                            logging.info(f'No SRR for {srp} found via pysradb')
                            store_missing_srr_in_db(database_holder, sra_project_id, PysradbError.NOT_FOUND, 'No SRR found')
                    except AttributeError as attribute_error:
                        logging.info(f'For SRP with id {sra_project_id}, pysradb produced attribute error with name {attribute_error.name}')
                        store_missing_srr_in_db(database_holder, sra_project_id, PysradbError.ATTRIBUTE_ERROR, str(attribute_error))
                    except TypeError as type_error:
                        logging.info(f'For SRP with id {sra_project_id}, pysradb produced type error with name {type_error}')
                        store_missing_srr_in_db(database_holder, sra_project_id, PysradbError.TYPE_ERROR, str(type_error))
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred: {str(exception)}')
        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def store_srrs_in_db(database_holder, srrs: [str], sra_project_id: int):
    try:
        srr_and_sra_id_tuples = [(sra_project_id, srr) for srr in srrs]
        logging.info(f'Tuples to insert {srr_and_sra_id_tuples}')
        database_holder.execute_bulk_write_statement('insert into sra_run (sra_project_id, srr) values (%s, %s) on conflict do nothing;', srr_and_sra_id_tuples)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def get_srp_sra_project(database_holder, sra_project_id: int) -> str:
    try:
        statement = f'select srp from sra_project where id=%s'
        parameters = (sra_project_id,)
        row = database_holder.execute_read_statement(statement, parameters)
        return row[0]
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def store_missing_srr_in_db(database_holder, sra_project_id: int, pysradb_error: PysradbError, details: str):
    try:
        pysradb_error_reference_id = get_pysradb_error_reference(database_holder, pysradb_error)
        statement = f'''insert into sra_run_missing (sra_project_id, pysradb_error_reference_id, details)
                        values (%s, %s, %s) on conflict do nothing;'''
        parameters = (sra_project_id, pysradb_error_reference_id, details)
        database_holder.execute_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def get_pysradb_error_reference(database_holder, pysradb_error: PysradbError) -> int:
    try:
        statement = f"select id from pysradb_error_reference where name=%s and operation='srp_to_srr';"
        parameters = (pysradb_error.value,)
        return database_holder.execute_read_statement(statement, parameters)[0]
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
