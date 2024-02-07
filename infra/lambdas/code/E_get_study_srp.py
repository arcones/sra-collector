import json
import logging
from enum import auto
from enum import Enum

import boto3
from env_params import env_params
from postgres_connection import postgres_connection
from pysradb import SRAweb


class PysradbError(Enum):
    ATTRIBUTE_ERROR = 'ATTRIBUTE_ERROR'
    VALUE_ERROR = 'VALUE_ERROR'


sqs = boto3.client('sqs', region_name='eu-central-1')


def handler(event, context):
    output_sqs, schema = env_params.params_per_env(context.function_name)

    if event:
        logging.info(f'Received event {event}')

        for record in event['Records']:
            study_with_missing_srp = json.loads(record['body'])
            study_id = study_with_missing_srp['study_id']
            request_id = study_with_missing_srp['request_id']
            logging.info(f'Received event {study_with_missing_srp}')

            gse = study_with_missing_srp['gse']
            try:
                raw_pysradb_response = SRAweb().gse_to_srp(gse)
                srp = raw_pysradb_response['study_accession'][0]

                if srp:
                    logging.info(f'SRP {srp} for GSE {gse} retrieved via pysradb for study {study_id}, pushing message to study summaries queue')
                    response = json.dumps({**study_with_missing_srp, 'srp': srp})
                    sqs.send_message(QueueUrl=output_sqs, MessageBody=response)
                    logging.info(f'Sent event to {output_sqs} with body {response}')
                    _store_srp_in_db(schema, request_id, gse, srp)
            except AttributeError as attribute_error:
                logging.warning(f'For study {study_id} with {gse}, pysradb produced attribute error with name {attribute_error.name}')
                _store_missing_srp_in_db(schema, request_id, gse, PysradbError.ATTRIBUTE_ERROR, str(attribute_error))
            except ValueError as value_error:
                logging.warning(f'For study {study_id} with {gse}, pysradb produced value error: {value_error}')
                _store_missing_srp_in_db(schema, request_id, gse, PysradbError.VALUE_ERROR, str(value_error))


def _store_srp_in_db(schema: str, request_id: str, gse: str, srp: str):
    database_connection = postgres_connection.get_connection()
    geo_study_id = _get_id_geo_study(schema, request_id, gse)
    cursor = database_connection.cursor()
    statement = cursor.mogrify(
        f'insert into {schema}.sra_project (srp, geo_study_id) values (%s, %s)',
        (srp, geo_study_id)
    )
    logging.debug(f'Executing: {statement}...')
    cursor.execute(statement)
    logging.info(f'Inserted sra project info in database')
    database_connection.commit()
    cursor.close()
    database_connection.close()


def _store_missing_srp_in_db(schema: str, request_id: str, gse: str, pysradb_error: PysradbError, details: str):
    database_connection = postgres_connection.get_connection()
    geo_study_id = _get_id_geo_study(schema, request_id, gse)
    pysradb_error_reference_id = _get_pysradb_error_reference(schema, pysradb_error)
    cursor = database_connection.cursor()
    statement = cursor.mogrify(
        f'insert into {schema}.sra_project_missing (geo_study_id, pysradb_error_reference_id, details) values (%s, %s, %s)',
        (geo_study_id, pysradb_error_reference_id, details)
    )
    logging.debug(f'Executing: {statement}...')
    cursor.execute(statement)
    logging.info(f'Inserted sra project info in database')
    database_connection.commit()
    cursor.close()
    database_connection.close()


def _get_id_geo_study(schema: str, request_id: str, gse: str) -> int:
    database_connection = postgres_connection.get_connection()
    cursor = database_connection.cursor()
    statement = cursor.mogrify(
        f'select id from {schema}.geo_study where request_id=%s and gse=%s',
        (request_id, gse)
    )
    logging.info(f'Executing: {statement}...')
    cursor.execute(statement)
    geo_study_id = cursor.fetchone()
    logging.info(f'Selected the geo_study row with id {geo_study_id}')
    cursor.close()
    database_connection.close()
    return geo_study_id


def _get_pysradb_error_reference(schema: str, pysradb_error: PysradbError) -> int:
    database_connection = postgres_connection.get_connection()
    cursor = database_connection.cursor()
    statement = cursor.mogrify(f'select id from {schema}.pysradb_error_reference where name=%s', (pysradb_error.value,))
    logging.info(f'Executing: {statement}...')
    cursor.execute(statement)
    pysradb_error_reference_id = cursor.fetchone()
    logging.info(f'Selected the geo_study row with id {pysradb_error_reference_id}')
    cursor.close()
    database_connection.close()
    return pysradb_error_reference_id
