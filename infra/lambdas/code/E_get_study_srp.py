import json
import logging
from enum import Enum

import boto3
from db_connection.db_connection import DBConnectionManager
from pysradb import SRAweb
from sqs_helper.sqs_helper import SQSHelper

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

sqs = boto3.client('sqs', region_name='eu-central-1')


class PysradbError(Enum):
    ATTRIBUTE_ERROR = 'ATTRIBUTE_ERROR'
    VALUE_ERROR = 'VALUE_ERROR'
    KEY_ERROR = 'KEY_ERROR'
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

                    geo_entity_id = int(request_body['geo_entity_id'])
                    gse = get_gse_geo_study(database_holder, geo_entity_id)

                    try:
                        raw_pysradb_response = SRAweb().gse_to_srp(gse)
                        srp = raw_pysradb_response['study_accession'][0]

                        if srp:
                            if srp.startswith('SRP'):
                                logging.info(f'SRP {srp} for GSE {gse} retrieved via pysradb, pushing message to study summaries queue')
                                sra_project_id = store_srp_in_db(database_holder, geo_entity_id, srp)
                                SQSHelper(sqs, context.function_name).send(message_body={'sra_project_id': sra_project_id})
                            else:
                                logging.info(f'For GSE {gse}, SRP {srp} is not compliant, skipping it.')
                                update_ncbi_study_srr_count(database_holder, geo_entity_id)
                        else:
                            logging.info(f'No SRP for {gse} found via pysradb')
                            store_missing_srp_and_srr_count(database_holder, geo_entity_id, PysradbError.NOT_FOUND, 'No SRP found')
                    except AttributeError as attribute_error:
                        logging.info(f'For {gse}, pysradb produced attribute error with name {attribute_error.name}')
                        store_missing_srp_and_srr_count(database_holder, geo_entity_id, PysradbError.ATTRIBUTE_ERROR, str(attribute_error))
                    except ValueError as value_error:
                        logging.info(f'For {gse}, pysradb produced value error: {value_error}')
                        store_missing_srp_and_srr_count(database_holder, geo_entity_id, PysradbError.VALUE_ERROR, str(value_error))
                    except KeyError as key_error:
                        logging.info(f'For {gse}, pysradb produced key error: {key_error}')
                        store_missing_srp_and_srr_count(database_holder, geo_entity_id, PysradbError.KEY_ERROR, str(key_error))
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')
        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def store_srp_in_db(database_holder, geo_entity_id: int, srp: str):
    try:
        write_statement = f'insert into sra_project (geo_study_id, srp) values (%s, %s) on conflict do nothing returning id;'
        parameters = (geo_entity_id, srp)
        operation_result = database_holder.execute_write_statement(write_statement, parameters)
        logging.info(f'operation result is {operation_result}')
        if operation_result: ## TODO aquimequede parece que esto rula, probar a ver si el G_ tb resolve algo
            logging.info('operation result is true')
            logging.info(f'operation result [0] is {operation_result[0]}')
            logging.info(f'operation result [0][0] is {operation_result[0][0]}')
            return operation_result[0][0]
        else:
            logging.info('operation result was false')
            read_statement = f'select id from sra_project where geo_study_id=%s and srp=%s;'  # TODO si esto va bien ponerlo en todos los bloques similares
            read_result = database_holder.execute_read_statement(read_statement, parameters)
            logging.info(f'read result is {read_result}')
            logging.info(f'read result [0] is {read_result[0]}')
            logging.info(f'read result [0][0] is {read_result[0][0]}')

            return read_result[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srp_in_db.__name__}: {str(exception)}')
        raise exception


def get_gse_geo_study(database_holder, geo_entity_id: int) -> str:
    try:
        statement = f'select gse from geo_study where id=%s;'  # TODO quitar todas las fstring q no son tal cosa
        return database_holder.execute_read_statement(statement, (geo_entity_id,))[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_gse_geo_study.__name__}: {str(exception)}')
        raise exception


def get_pysradb_error_reference(database_holder, pysradb_error: PysradbError) -> int:
    try:
        statement = f"select id from pysradb_error_reference where name=%s and operation='gse_to_srp';"
        parameters = (pysradb_error.value,)
        return database_holder.execute_read_statement(statement, parameters)[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_pysradb_error_reference.__name__}: {str(exception)}')
        raise exception


def store_missing_srp_and_srr_count(database_holder, geo_entity_id: int, pysradb_error: PysradbError, details: str):
    try:
        store_missing_srp_in_db(database_holder, geo_entity_id, pysradb_error, details)
        update_ncbi_study_srr_count(database_holder, geo_entity_id)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_missing_srp_and_srr_count.__name__}: {str(exception)}')
        raise exception


def store_missing_srp_in_db(database_holder, geo_entity_id: int, pysradb_error: PysradbError, details: str):
    try:
        pysradb_error_reference_id = get_pysradb_error_reference(database_holder, pysradb_error)
        statement = f'''insert into sra_project_missing (geo_study_id, pysradb_error_reference_id, details)
                        values (%s, %s, %s) on conflict do nothing;'''
        parameters = (geo_entity_id, pysradb_error_reference_id, details)
        database_holder.execute_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_missing_srp_in_db.__name__}: {str(exception)}')
        raise exception


def update_ncbi_study_srr_count(database_holder, geo_entity_id: int):
    try:
        statement = 'update ncbi_study set srr_metadata_count=0 where id=(select ncbi_study_id from geo_study where id=%s)'
        database_holder.execute_write_statement(statement, (geo_entity_id,))
    except Exception as exception:
        logging.error(f'An exception has occurred in {update_ncbi_study_srr_count.__name__}: {str(exception)}')
        raise exception
