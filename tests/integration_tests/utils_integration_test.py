import json
import time

import boto3
import psycopg2
import urllib3

http = urllib3.PoolManager()

secrets = boto3.client('secretsmanager', region_name='eu-central-1')


def wait_test_server_readiness():
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


def store_test_request(database_holder, request_id, ncbi_query):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into request (id, query, geo_count, mail) values (%s, %s, %s, %s);', (request_id, ncbi_query, 1, 'arconestech@gmail.com'))  ## TODO se va a quedar esto asi
    database_connection.commit()


def stores_test_ncbi_study(database_holder, request_id, ncbi_id):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into ncbi_study (request_id, ncbi_id) values (%s, %s) returning id;', (request_id, ncbi_id))
    database_connection.commit()
    return database_cursor.fetchone()[0]


def store_test_geo_study(database_holder, study_id, gse):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into geo_study (ncbi_study_id, gse) values (%s, %s) returning id;', (study_id, gse))
    database_connection.commit()
    return database_cursor.fetchone()[0]


def store_test_sra_project(database_holder, geo_study_id, srp):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into sra_project (geo_study_id, srp) values (%s, %s) returning id;', (geo_study_id, srp))
    inserted_sra_project_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_sra_project_id


def store_test_sra_run(database_holder, sra_project_id, srr):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into sra_run (sra_project_id, srr) values (%s, %s) returning id;', (sra_project_id, srr))
    database_connection.commit()
    return database_cursor.fetchone()[0]


def store_test_sra_run_metadata(database_holder, sra_run_id):
    database_connection, database_cursor = database_holder
    database_cursor.execute(
        'insert into sra_run_metadata (sra_run_id, spots, bases, organism) values (%s, %s, %s, %s) returning id;',
        (sra_run_id, 39832, 93809832, 'ser ser')
    )
    database_connection.commit()
    sra_run_metadata_id = database_cursor.fetchone()[0]
    database_cursor.execute(
        'insert into sra_run_metadata_phred (sra_run_metadata_id, score, read_count) values (%s, %s, %s);',
        (sra_run_metadata_id, 37, 100)
    )
    database_cursor.execute(
        ('insert into sra_run_metadata_statistic_read (sra_run_metadata_id, nspots, layout,'
         'read_0_count, read_0_average, read_0_stdev, read_1_count, read_1_average, read_1_stdev) '
         'values (%s, %s, %s,%s, %s, %s, %s, %s, %s)'
         ),
        (sra_run_metadata_id, 9832, 'SINGLE', 4237, 2.56, 3.222, 0, 0, 0)
    )
    database_connection.commit()
