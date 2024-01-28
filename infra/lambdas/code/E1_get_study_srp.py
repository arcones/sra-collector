import json
import logging

import boto3
from postgres_connection import postgres_connection
from pysradb import SRAweb

sqs = boto3.client('sqs', region_name='eu-central-1')

output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/srps_queue'


def handler(event, context):
    try:
        if event:
            logging.info(f'Received event {event}')

            for record in event['Records']:
                study_with_missing_srp = json.loads(record['body'])
                study_id = study_with_missing_srp['study_id']
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
                        _store_srp_in_db(srp, study_with_missing_srp['request_id'], gse)
                except AttributeError as key_error:
                    logging.error(f'For study {study_id} with {gse}, pysradb produced attribute error with name {key_error.name}')
                except KeyError as key_error:
                    logging.error(f'For study {study_id} with {gse}, pysradb produced key error: {key_error}')
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')


def _store_srp_in_db(srp: str, request_id: str, gse: str):
    try:
        database_connection = postgres_connection.get_connection()
        geo_study_id = _get_id_geo_study(request_id, gse)
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            'insert into sra_project (srp, geo_study_id) values (%s, %s)',
            (srp, geo_study_id)
        )
        logging.debug(f'Executing: {statement}...')
        cursor.execute(statement)
        logging.info(f'Inserted sra project info in database')
        database_connection.commit()
        cursor.close()
        database_connection.close()
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')


def _get_id_geo_study(request_id: str, gse: str):
    try:
        database_connection = postgres_connection.get_connection()
        cursor = database_connection.cursor()
        statement = cursor.mogrify(
            'select id from geo_study where request_id=%s and gse=%s',
            (request_id, gse)
        )
        logging.info(f'Executing: {statement}...')
        cursor.execute(statement)
        geo_study_id = cursor.fetchone()
        logging.info(f'Selected the geo_study row with id {geo_study_id}')
        cursor.close()
        database_connection.close()
        return geo_study_id
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
