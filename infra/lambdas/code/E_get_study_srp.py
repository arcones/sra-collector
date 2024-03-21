import inspect
import json
import logging
import os
from enum import Enum

import boto3
from db_connection.db_connection import DBConnectionManager
from pysradb import SRAweb

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)


class PysradbError(Enum):
    ATTRIBUTE_ERROR = 'ATTRIBUTE_ERROR'
    VALUE_ERROR = 'VALUE_ERROR'
    KEY_ERROR = 'KEY_ERROR'
    NOT_FOUND = 'NOT_FOUND'


sqs = boto3.client('sqs', region_name='eu-central-1')

if os.environ['ENV'] == 'prod':
    output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/E_srps'
else:
    output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/integration_test_queue'


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

                    geo_entity_id = int(request_body['geo_entity_id'])
                    gse = get_gse_geo_study(database_holder, geo_entity_id)

                    try:
                        raw_pysradb_response = SRAweb().gse_to_srp(gse)
                        srp = raw_pysradb_response['study_accession'][0]

                        if srp:
                            if srp.startswith('SRP'):
                                logging.info(f'SRP {srp} for GSE {gse} retrieved via pysradb, pushing message to study summaries queue')
                                sra_project_id = store_srp_in_db(database_holder, geo_entity_id, srp)
                                response = json.dumps({'sra_project_id': sra_project_id})
                                sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                                logging.info(f'Sent event to {output_sqs} with body {response}')
                            else:
                                logging.info(f'For GSE {gse}, SRP {srp} is not compliant, skipping it.')
                        else:
                            logging.info(f'No SRP for {gse} found via pysradb')
                            store_missing_srp_in_db(database_holder, geo_entity_id, PysradbError.NOT_FOUND, 'No SRP found')
                    except AttributeError as attribute_error:
                        logging.info(f'For {gse}, pysradb produced attribute error with name {attribute_error.name}')
                        store_missing_srp_in_db(database_holder, geo_entity_id, PysradbError.ATTRIBUTE_ERROR, str(attribute_error))
                    except ValueError as value_error:
                        logging.info(f'For {gse}, pysradb produced value error: {value_error}')
                        store_missing_srp_in_db(database_holder, geo_entity_id, PysradbError.VALUE_ERROR, str(value_error))
                    except KeyError as key_error:
                        logging.info(f'For {gse}, pysradb produced key error: {key_error}')
                        store_missing_srp_in_db(database_holder, geo_entity_id, PysradbError.KEY_ERROR, str(key_error))
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def store_srp_in_db(database_holder, geo_entity_id: int, srp: str):
    try:
        sra_project_id = get_id_sra_project(database_holder, srp)
        if not sra_project_id:
            statement = f'insert into sra_project (srp) values (%s) on conflict do nothing returning id;'
            sra_project_id = database_holder.execute_write_statement(statement, (srp,))[0]
        statement = f'insert into geo_study_sra_project_link (geo_study_id, sra_project_id) values (%s, %s) on conflict do nothing;'
        parameters = (geo_entity_id, sra_project_id)
        database_holder.execute_write_statement(statement, parameters)
        return sra_project_id
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srp_in_db.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception


def get_id_sra_project(database_holder, srp: str) -> int:
    try:
        statement = f'select max(id) from sra_project where srp=%s;'
        return database_holder.execute_read_statement(statement, (srp,))[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_id_sra_project.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception


def get_gse_geo_study(database_holder, geo_entity_id: int) -> str:
    try:
        statement = f'select gse from geo_study where id=%s;'
        return database_holder.execute_read_statement(statement, (geo_entity_id,))[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_gse_geo_study.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception


def store_missing_srp_in_db(database_holder, geo_entity_id: int, pysradb_error: PysradbError, details: str):
    try:
        pysradb_error_reference_id = get_pysradb_error_reference(database_holder, pysradb_error)
        statement = f'''insert into sra_project_missing (geo_study_id, pysradb_error_reference_id, details)
                        values (%s, %s, %s) on conflict do nothing;'''
        parameters = (geo_entity_id, pysradb_error_reference_id, details)
        database_holder.execute_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_missing_srp_in_db.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception


def get_pysradb_error_reference(database_holder, pysradb_error: PysradbError) -> int:
    try:
        statement = f"select id from pysradb_error_reference where name=%s and operation='gse_to_srp';"
        parameters = (pysradb_error.value,)
        return database_holder.execute_read_statement(statement, parameters)[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_pysradb_error_reference.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception
