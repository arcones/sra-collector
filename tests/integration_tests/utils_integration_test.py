import json
import time

import boto3
import psycopg2
import urllib3

http = urllib3.PoolManager()

secrets = boto3.client('secretsmanager', region_name='eu-central-1')


def _wait_test_server_readiness():
    is_test_still_initializing = True
    start_waiting = time.time()
    while is_test_still_initializing:
        try:
            response = http.urlopen('GET', 'http://localhost:3001')
            if response.status == 404:
                print('Test server is ready :)')
                is_test_still_initializing = False
        except Exception as connection_refused_error:
            if time.time() - start_waiting < 60:
                print('Tests are still initializing...')
                time.sleep(1)
            else:
                print('Timeout while waiting test server to launch :(')
                raise connection_refused_error


class PostgreConnectionManager:
    def __init__(self):
        self.database_credentials = secrets.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
        self.username = json.loads(self.database_credentials['SecretString'])['username']
        self.password = json.loads(self.database_credentials['SecretString'])['password']
        self.host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'
        self.connection_string = f"host={self.host} dbname='sracollector' user='{self.username}' password='{self.password}'"
        self.database_connection = None
        self.database_cursor = None

    def __enter__(self):
        self.database_connection = psycopg2.connect(self.connection_string)
        self.database_cursor = self.database_connection.cursor()
        self.database_cursor.execute("SET search_path TO 'sracollector-dev'")
        return self.database_connection, self.database_cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.database_cursor:
            self.database_cursor.close()
        if self.database_connection:
            self.database_connection.close()


def _store_test_request(database_holder, request_id, ncbi_query):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into request (id, query, geo_count) values (%s, %s, %s);', (request_id, ncbi_query, 1))
    database_connection.commit()


def _stores_test_ncbi_study(database_holder, request_id, ncbi_id):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into ncbi_study (request_id, ncbi_id) values (%s, %s) returning id;', (request_id, ncbi_id))
    database_connection.commit()
    return database_cursor.fetchone()[0]
