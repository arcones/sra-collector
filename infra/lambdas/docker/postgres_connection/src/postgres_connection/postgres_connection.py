import json
import logging
import time

import boto3
import psycopg2
from psycopg2 import errors
from psycopg2 import OperationalError
from psycopg2.errorcodes import UNIQUE_VIOLATION

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

DB_CONNECTION_MAX_TRIES = 5

secrets = boto3.client('secretsmanager', region_name='eu-central-1')

logger = logging.getLogger(__name__)


def get_database_holder():
    database_connection = _get_connection()
    database_cursor = database_connection.cursor()
    return database_connection, database_cursor


def execute_write_statement(database_connection, database_cursor, statement: str):
    try:
        logger.info(f'Executing: {statement}...')
        database_cursor.execute(statement)
        logger.info(f'Executed {statement}')
        database_connection.commit()
    except errors.lookup(UNIQUE_VIOLATION) as unique_violation:
        logger.warning(f'The {statement} failed with unique violation: {unique_violation}')
    database_cursor.close()
    database_connection.close()


def execute_bulk_write_statement(database_connection, database_cursor, statement_pattern: str, tuples: [tuple]):
    logger.info(f'Executing {len(tuples)} statements with SQL {statement_pattern}...')
    for the_tuple in tuples:
        mogrified_statement = database_cursor.mogrify(statement_pattern, the_tuple)
        try:
            logger.info(f'Executing: {mogrified_statement}...')
            database_cursor.execute(mogrified_statement)
            logger.info(f'Executed {mogrified_statement}')
            database_connection.commit()
        except errors.lookup(UNIQUE_VIOLATION) as unique_violation:
            logger.warning(f'The {mogrified_statement} failed with unique violation: {unique_violation}')
    database_cursor.close()
    database_connection.close()


def execute_read_statement_for_primary_key(database_connection, database_cursor, statement: str) -> int:
    logger.info(f'Executing: {statement}...')
    result_id = None
    while result_id is None:
        database_cursor.execute(statement)
        result_id = database_cursor.fetchone()
        if result_id is None:
            time.sleep(1)
    logger.info(f'Executed {statement}')
    database_cursor.close()
    database_connection.close()
    return result_id


def _get_connection():
    database_credentials = secrets.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
    username = json.loads(database_credentials['SecretString'])['username']
    password = json.loads(database_credentials['SecretString'])['password']
    host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'

    connection_string = f"host={host} dbname='sracollector' user='{username}' password='{password}'"

    database_connection = None
    connection_tries = 0

    while database_connection is None:
        try:
            database_connection = psycopg2.connect(connection_string)
            logger.info(f'Successfully connected with database in try #{connection_tries}')
        except OperationalError as operationalError:
            if connection_tries == DB_CONNECTION_MAX_TRIES:
                logger.error(f'Not able to connect with database after {connection_tries} attempts')
                logger.error(str(operationalError))
                raise operationalError
            else:
                logger.warning(f'Not able to connect with database in try #{connection_tries}')
                logger.warning(str(operationalError))
                connection_tries += 1
                time.sleep(1)

    return database_connection
