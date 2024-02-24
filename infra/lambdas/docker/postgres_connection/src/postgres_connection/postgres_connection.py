import hashlib
import json
import logging
import os
import time
from io import StringIO

import boto3
import psycopg2
from psycopg2 import OperationalError

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

MAX_TRIES = 5

secrets = boto3.client('secretsmanager', region_name='eu-central-1')

logger = logging.getLogger(__name__)


def schema_for_env() -> str:
    sqs_name = 'integration_test_queue'
    db_schema = 'sracollector_dev'
    if os.environ['ENV'] == 'prod':
        db_schema = 'sracollector'

    logger.debug(f'DB schema in use is {db_schema}')

    return db_schema


def execute_write_statement(statement: str, parameters: tuple):
    write_command_output = None
    database_connection = _get_connection()
    database_cursor = database_connection.cursor()
    try:
        logger.info(f'Executing: {statement} with parameters {parameters}...')
        database_cursor.execute(statement, parameters)
        logger.info(f'Executed {statement} with parameters {parameters}')
        database_connection.commit()
        return write_command_output
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
    finally:
        database_cursor.close()
        database_connection.close()


def execute_write_statement_returning(statement: str, parameters: tuple):
    write_command_output = None
    database_connection = _get_connection()
    database_cursor = database_connection.cursor()
    try:
        logger.info(f'Executing: {statement} with parameters {parameters}...')
        database_cursor.execute(statement, parameters)
        write_command_output = database_cursor.fetchone()[0]
        logger.info(f'Executed {statement} with parameters {parameters}')
        database_connection.commit()
        return write_command_output
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
    finally:
        database_cursor.close()
        database_connection.close()


def execute_bulk_write_statement(schema: str, destination_table: str, columns: [str], rows: [tuple]):
    database_connection = _get_connection()
    database_cursor = database_connection.cursor()
    tuple_length = max([len(row) for row in rows])
    assert tuple_length == len(columns), "The tuples provided don't have the same size as the columns"

    logger.info(f'Inserting {len(rows)} in {destination_table}')
    try:
        file = StringIO()
        for row in rows:
            file.write('\t'.join(map(str, row)) + '\n')
        file.seek(0)
        file_hash = hashlib.md5(file.getvalue().encode('utf-8')).hexdigest()
        logger.info(f'Executing bulk insert with file hash "{file_hash}"')
        sql = f"COPY {schema}.{destination_table} ({','.join(columns)}) FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t')"
        database_cursor.copy_expert(sql, file)
        logger.info(f'Executed bulk insert')
        database_connection.commit()
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
    finally:
        database_cursor.close()
        database_connection.close()


def execute_read_statement_for_primary_key(statement: str, parameters: tuple) -> int:
    database_connection = _get_connection()
    database_cursor = database_connection.cursor()
    try:
        logger.info(f'Executing: {statement} with parameters {parameters}...')
        database_cursor.execute(statement, parameters)
        logger.info(f'Executed {statement} with parameters {parameters}')
        return database_cursor.fetchone()[0] if database_cursor.rowcount > 0 else None
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
    finally:
        database_cursor.close()
        database_connection.close()


def is_row_present(statement: str, parameters: tuple) -> bool:
    database_connection = _get_connection()
    database_cursor = database_connection.cursor()
    try:
        logger.info(f'Executing: {statement} with parameters {parameters}...')
        database_cursor.execute(statement, parameters)
        result = database_cursor.fetchone()
        logger.info(f'Executed {statement} with parameters {parameters}')
        return result is not None
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
    finally:
        database_cursor.close()
        database_connection.close()


def _get_connection():
    database_credentials = secrets.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
    username = json.loads(database_credentials['SecretString'])['username']
    password = json.loads(database_credentials['SecretString'])['password']
    host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'

    connection_string = f"host={host} dbname='sracollector' user='{username}' password='{password}'"

    database_connection = None
    connection_attempts = 0

    while database_connection is None:
        try:
            database_connection = psycopg2.connect(connection_string)
            logger.info(f'Successfully connected with database in attempt #{connection_attempts}')
        except OperationalError as operationalError:
            if connection_attempts == MAX_TRIES:
                logger.error(f'Not able to connect with database after {connection_attempts} attempts')
                logger.error(str(operationalError))
                raise operationalError
            else:
                logger.warning(f'Not able to connect with database in attempt #{connection_attempts}')
                logger.warning(str(operationalError))
                connection_attempts += 1
                time.sleep(1)
    return database_connection
