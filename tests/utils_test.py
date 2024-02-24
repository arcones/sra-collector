import json
import random
import string
import time

import boto3
import psycopg2
import urllib3

http = urllib3.PoolManager()

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits

class Context:
    def __init__(self, function_name):
        self.function_name = function_name


def _get_db_connection():
    secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
    database_credentials = secrets_client.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
    secrets_client.close()
    username = json.loads(database_credentials['SecretString'])['username']
    password = json.loads(database_credentials['SecretString'])['password']
    host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'

    connection_string = f"host={host} dbname='sracollector' user='{username}' password='{password}'"
    print('DB connection ready :)')
    return psycopg2.connect(connection_string)


def _provide_random_request_id():
    return ''.join(random.choice(CHARACTERS) for char in range(20))


def _provide_random_ncbi_query():
    return ''.join(random.choice(CHARACTERS) for char in range(50))


def _store_test_request(database_holder, request_id, ncbi_query):
    database_cursor, database_connection = database_holder

    request_statement = database_cursor.mogrify('insert into sracollector_dev.request (id, query, geo_count) values (%s, %s, %s)', (request_id, ncbi_query, 1))
    database_cursor.execute(request_statement)
    database_connection.commit()


def _store_test_geo_study(database_holder, request_id, study_id, gse):
    database_cursor, database_connection = database_holder

    study_statement = database_cursor.mogrify('insert into sracollector_dev.geo_study (request_id, ncbi_id, gse) values (%s, %s, %s) returning id',
                                              (request_id, study_id, gse))
    database_cursor.execute(study_statement)
    inserted_geo_study_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_geo_study_id


def _store_test_geo_experiment(database_holder, request_id, study_id, gsm):
    database_cursor, database_connection = database_holder

    study_statement = database_cursor.mogrify('insert into sracollector_dev.geo_experiment (request_id, ncbi_id, gsm) values (%s, %s, %s) returning id',
                                              (request_id, study_id, gsm))
    database_cursor.execute(study_statement)
    inserted_geo_experiment_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_geo_experiment_id


def _store_test_geo_platform(database_holder, request_id, study_id, gpl):
    database_cursor, database_connection = database_holder

    study_statement = database_cursor.mogrify('insert into sracollector_dev.geo_platform (request_id, ncbi_id, gpl) values (%s, %s, %s) returning id',
                                              (request_id, study_id, gpl))
    database_cursor.execute(study_statement)
    inserted_geo_platform_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_geo_platform_id


def _store_test_geo_data_set(database_holder, request_id, study_id, gds):
    database_cursor, database_connection = database_holder

    study_statement = database_cursor.mogrify('insert into sracollector_dev.geo_data_set (request_id, ncbi_id, gds) values (%s, %s, %s) returning id',
                                              (request_id, study_id, gds))
    database_cursor.execute(study_statement)
    inserted_geo_data_set = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_geo_data_set


def _store_test_sra_project(database_holder, srp, geo_study_id):
    database_cursor, database_connection = database_holder

    project_statement = database_cursor.mogrify('insert into sracollector_dev.sra_project (srp) values (%s) returning id', (srp,))
    database_cursor.execute(project_statement)
    inserted_sra_project_id = database_cursor.fetchone()[0]
    link_statement = database_cursor.mogrify('insert into sracollector_dev.geo_study_sra_project_link (geo_study_id, sra_project_id) values (%s, %s)',
                                             (geo_study_id, inserted_sra_project_id))
    database_cursor.execute(link_statement)
    database_connection.commit()
    return inserted_sra_project_id


def _store_test_sra_run(database_holder, srr, sra_project_id):
    database_cursor, database_connection = database_holder

    run_statement = database_cursor.mogrify('insert into sracollector_dev.sra_run (srr, sra_project_id) values (%s, %s) returning id',
                                            (srr, sra_project_id))
    database_cursor.execute(run_statement)
    inserted_sra_run_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_sra_run_id


def _get_needed_batches_of_ten_messages(messages_count):
    batches, remainder = divmod(messages_count, 10)
    if remainder > 0:
        batches += 1
    return batches


def _get_customized_input_from_sqs(bodies: [str]) -> dict:
    sqs_message_without_body = {
        'messageId': 'fe1e0334-c5c1-4e76-975a-832c16dd4c1c',
        'receiptHandle': 'AQEB503JmCqXJ6XSLNL+M7tdFRPpON7z6JPhiYOy+fNv3iN22QHAGFasCcajuIjOq3s5/6lDIBnoE6cFPeRc7A3yT/rmqkehpnkxFIYqGOwXeOnM0FoKDd39aNiybjAD7ADL1kW9jpqu4PaiDVQKCI0+v3McJVfdGayROAXGFcgAcO9BX5HbyevJpKU9C+pVQCwcDmXVawP53TuZeWjVwOLG+SgdqGpNCKYD4kjOIC060bsSek3MoMrKQx+huXSvz+Nrs6OQa4fdJ9c/M3zb9sbaIaYd5d2GMTegQZPgxyEHdLdoI1v9eGqDvIP21kQD4Q8y/Xf1vT4PIXTkgHV1f5m1ccn5wXO8XyAvzc6/BdgL8r4lAYLDYFTYMpnH+35Qs2hwXP3jh8SbcfzFNUEV22rjDw==',
        'attributes': {
            'ApproximateReceiveCount': '1',
            'AWSTraceHeader': 'Root=1-65be78eb-7a59c90254665fce0b0fc5aa;Parent=3856816849320e54;Sampled=0;Lineage=2dfc983d:0',
            'SentTimestamp': '1706981613100',
            'SenderId': 'AROARYGZXFUU2YMSEOV67:foo_bar',
            'ApproximateFirstReceiveTimestamp': '1706981613105'
        },
        'messageAttributes': {},
        'md5OfBody': 'b8852234cf7aad8b1086dd58a47a616b',
        'eventSource': 'aws:sqs',
        'eventSourceARN': 'arn:aws:sqs:eu-central-1:120715685161:kilombo',
        'awsRegion': 'eu-central-1'
    }

    return {'Records': [{**sqs_message_without_body, 'body': body} for body in bodies]}
