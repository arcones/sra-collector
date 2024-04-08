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
                            sra_run_ids = store_srrs_and_count(database_holder, srrs, sra_project_id)

                            message_bodies = [{'sra_run_id': sra_run_id} for sra_run_id in sra_run_ids]

                            SQSHelper(sqs, context.function_name).send(message_bodies=message_bodies)

                        else:
                            logging.info(f'No SRR for {srp} found via pysradb')
                            store_missing_srr_and_count(database_holder, sra_project_id, PysradbError.NOT_FOUND, 'No SRR found')
                    except AttributeError as attribute_error:
                        logging.info(f'For SRP with id {sra_project_id}, pysradb produced attribute error with name {attribute_error.name}')
                        store_missing_srr_and_count(database_holder, sra_project_id, PysradbError.ATTRIBUTE_ERROR, str(attribute_error))
                    except TypeError as type_error:
                        logging.info(f'For SRP with id {sra_project_id}, pysradb produced type error with name {type_error}')
                        store_missing_srr_and_count(database_holder, sra_project_id, PysradbError.TYPE_ERROR, str(type_error))
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')
        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def store_srrs_and_count(database_holder, srrs: [str], sra_project_id: int):
    try:
        srr_and_sra_id_tuples = store_srrs_in_db(database_holder, srrs, sra_project_id)
        update_ncbi_study_srr_count(database_holder, sra_project_id, len(srrs))
        return srr_and_sra_id_tuples
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srrs_and_count.__name__}: {str(exception)}')
        raise exception


def store_srrs_in_db(database_holder, srrs: [str], sra_project_id: int):
    try:
        write_statement = 'insert into sra_run (sra_project_id, srr) values (%s, %s) on conflict do nothing returning id;'
        parameters = [(sra_project_id, srr) for srr in srrs]
        operation_result = database_holder.execute_bulk_write_statement(write_statement, parameters)
        if operation_result:
            return operation_result
        else:
            read_statement = 'select id from sra_run where sra_project_id=%s and srr=%s;'
            return database_holder.execute_read_statement(read_statement, parameters)[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srrs_in_db.__name__}: {str(exception)}')
        raise exception


def get_srp_sra_project(database_holder, sra_project_id: int) -> str:
    try:
        statement = f'select srp from sra_project where id=%s'
        parameters = (sra_project_id,)
        return database_holder.execute_read_statement(statement, parameters)[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_srp_sra_project.__name__}: {str(exception)}')
        raise exception


def store_missing_srr_and_count(database_holder, sra_project_id: int, pysradb_error: PysradbError, details: str):
    try:
        store_missing_srr_in_db(database_holder, sra_project_id, pysradb_error, details)
        update_ncbi_study_srr_count(database_holder, sra_project_id, 0)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_missing_srr_and_count.__name__}: {str(exception)}')
        raise exception


def update_ncbi_study_srr_count(database_holder, sra_project_id: int, srr_metadata_count: int):
    try:
        statement = ('update ncbi_study set srr_metadata_count=%s '
                     'where id=('
                     'select ncbi_study_id from geo_study gs '
                     'join sra_project sp on sp.geo_study_id = gs.id '
                     'where sp.id=%s)')
        database_holder.execute_write_statement(statement, (srr_metadata_count, sra_project_id))
    except Exception as exception:
        logging.error(f'An exception has occurred in {update_ncbi_study_srr_count.__name__}: {str(exception)}')
        raise exception


def store_missing_srr_in_db(database_holder, sra_project_id: int, pysradb_error: PysradbError, details: str):
    try:
        pysradb_error_reference_id = get_pysradb_error_reference(database_holder, pysradb_error)
        statement = f'''insert into sra_run_missing (sra_project_id, pysradb_error_reference_id, details)
                        values (%s, %s, %s) on conflict do nothing;'''
        parameters = (sra_project_id, pysradb_error_reference_id, details)
        database_holder.execute_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_missing_srr_in_db.__name__}: {str(exception)}')
        raise exception


def get_pysradb_error_reference(database_holder, pysradb_error: PysradbError) -> int:
    try:
        statement = f"select id from pysradb_error_reference where name=%s and operation='srp_to_srr';"
        parameters = (pysradb_error.value,)
        return database_holder.execute_read_statement(statement, parameters)[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_pysradb_error_reference.__name__}: {str(exception)}')
        raise exception
