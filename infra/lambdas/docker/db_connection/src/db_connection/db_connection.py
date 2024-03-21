import inspect
import json
import logging
import os
import re
import time

import boto3
import psycopg2
from psycopg2 import OperationalError
from psycopg2 import ProgrammingError

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)

secrets = boto3.client('secretsmanager', region_name='eu-central-1')

logger = logging.getLogger(__name__)


class DBConnectionManager:
    def __init__(self):
        if os.environ['ENV'] == 'prod' or os.environ['ENV'] == 'integration-test':
            self.database_credentials = secrets.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
            self.username = json.loads(self.database_credentials['SecretString'])['username']
            self.password = json.loads(self.database_credentials['SecretString'])['password']
            self.host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'
            self.connection_string = f"host={self.host} dbname='sracollector' user='{self.username}' password='{self.password}'"
            self.database_connection = None
            self.database_cursor = None
            self.connection_attempts = 0
            self.MAX_TRIES = 5
        elif os.environ['ENV'] == 'unit-test':
            self.url = 'jdbc:h2:./tmp/test-db/test.db;MODE=PostgreSQL'
            self.jar_path = './db/h2-2.2.224.jar'
            self.driver = 'org.h2.Driver'
            self.credentials = ['', '']
            self.database_connection = None
            self.database_cursor = None

    def __enter__(self):
        if os.environ['ENV'] == 'prod':
            self.initialize_postgres()
            self.database_cursor.execute("SET search_path TO 'sracollector'")
        elif os.environ['ENV'] == 'integration-test':
            self.initialize_postgres()
            self.database_cursor.execute("SET search_path TO 'sracollector-dev'")
        elif os.environ['ENV'] == 'unit-test':
            import jaydebeapi
            self.database_connection = jaydebeapi.connect(self.driver, self.url, self.credentials, self.jar_path)
            self.database_cursor = self.database_connection.cursor()

        return self

    def initialize_postgres(self):
        while self.database_connection is None:
            try:
                self.database_connection = psycopg2.connect(self.connection_string)
                logger.info(f'Successfully connected with database in attempt #{self.connection_attempts}')
            except OperationalError as operationalError:
                if self.connection_attempts == self.MAX_TRIES:
                    logger.error(f'Not able to connect with database after {self.connection_attempts} attempts')
                    logger.error(str(operationalError))
                    raise operationalError
                else:
                    logger.warning(f'Not able to connect with database in attempt #{self.connection_attempts}')
                    logger.warning(str(operationalError))
                    self.connection_attempts += 1
                    time.sleep(1)
        self.database_cursor = self.database_connection.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.database_cursor:
            self.database_cursor.close()
        if self.database_connection:
            self.database_connection.close()

    def execute_read_statement(self, statement: str, parameters: tuple):
        try:
            logger.info(f'Executing: {statement} with parameters {parameters}...')
            result = self._cursor_execute_single_and_return(statement, parameters)
            logger.info(f'Executed {statement} with parameters {parameters}')
            return result
        except Exception as exception:
            logging.error(f'An exception has occurred in {self.execute_read_statement.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
            raise exception

    def execute_write_statement(self, statement: str, parameters: tuple):
        try:
            logger.info(f'Executing: {statement} with parameters {parameters}...')
            result = self._cursor_execute_single_and_return(statement, parameters)
            logger.info(f'Executed {statement} with parameters {parameters}')
            self.database_connection.commit()
            return result
        except Exception as exception:
            logging.error(f'An exception has occurred in {self.execute_write_statement.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
            raise exception

    def execute_bulk_write_statement(self, statement: str, parameters: [tuple]):
        try:
            logger.info(f'Executing: {statement} with parameters {parameters}...')
            result = self._cursor_execute_multiple_and_return(statement, parameters)
            logger.info(f'Executed {statement} with parameters {parameters}')
            self.database_connection.commit()
            return result
        except Exception as exception:
            logging.error(f'An exception has occurred in {self.execute_bulk_write_statement.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
            raise exception

    def _cursor_execute_single_and_return(self, statement, parameters) -> None | tuple:
        result = None
        if os.environ['ENV'] == 'prod' or os.environ['ENV'] == 'integration-test':
            self.database_cursor.execute(statement, parameters)
            try:
                result = self.database_cursor.fetchone()
            except ProgrammingError:
                pass
        elif os.environ['ENV'] == 'unit-test':
            statement_2_parameters = _adapt_statement_to_env(statement, parameters)
            for statement, parameters in statement_2_parameters.items():
                if _is_select(statement):
                    self.database_cursor.execute(statement, parameters)
                    result = self.database_cursor.fetchone()
                else:
                    self.database_cursor.execute(statement, parameters)
        return result

    def _cursor_execute_multiple_and_return(self, statement, parameters) -> [tuple]:
        result = []
        if os.environ['ENV'] == 'prod' or os.environ['ENV'] == 'integration-test':
            for parameter in parameters:
                self.database_cursor.execute(statement, parameter)
                try:
                    inserted_id = self.database_cursor.fetchone()
                    result.append(inserted_id)
                except ProgrammingError:
                    pass
        elif os.environ['ENV'] == 'unit-test':
            statement_2_parameters = _adapt_statement_to_env(statement, parameters)
            for statement, parameter_groups in statement_2_parameters.items():
                if _is_select(statement):
                    for parameter_group in parameter_groups:
                        self.database_cursor.execute(statement, parameter_group)
                        result.append(self.database_cursor.fetchone())
                else:
                    self.database_cursor.executemany(statement, parameter_groups)
        return result


def _handle_insert_returning_clause(statement, parameters):
    if 'returning id' in statement:
        pattern = re.compile(r'insert +into +(\w+) +\((.*)\) +values.*', re.IGNORECASE)
        matches = pattern.search(statement)
        select_table = matches.group(1)
        select_columns = matches.group(2).split(',')

        aux_select = f'select id from {select_table} where '

        for index, select_column in enumerate(select_columns):
            if index == 0:
                aux_select += f'{select_column}=? '
            else:
                aux_select += f'and {select_column}=? '

        adapted_insert = statement.replace('returning id', '')

        return {adapted_insert: parameters, aux_select: parameters}
    else:
        return {statement: parameters}


def _adapt_statement_to_h2_syntax(statement):
    adapted_statement = statement.replace('%s', '?').replace('\n', '')
    on_conflict_pattern = r'on +conflict +do +nothing'
    return re.sub(on_conflict_pattern, '', adapted_statement)


def _adapt_statement_to_env(statement, parameters):
    statement_2_parameters = {statement: parameters}

    if os.environ['ENV'] != 'prod':
        statement = _adapt_statement_to_h2_syntax(statement)
        statement_2_parameters = _handle_insert_returning_clause(statement, list(parameters))

    return statement_2_parameters


def _is_select(statement):
    return statement.lower().startswith('select')
