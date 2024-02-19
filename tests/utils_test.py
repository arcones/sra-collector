import json
import random
import string
import time

import boto3
import psycopg2
import urllib3

http = urllib3.PoolManager()

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits


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


def _ensure_queue_is_empty(sqs_client, queue):
    messages_left = None
    start_waiting = time.time()
    while messages_left != 0:
        response = sqs_client.get_queue_attributes(QueueUrl=queue, AttributeNames=['ApproximateNumberOfMessages'])
        messages_left = int(response['Attributes']['ApproximateNumberOfMessages'])
        if time.time() - start_waiting < 60:
            print('SQS queue is still not empty...')
            time.sleep(1)
        else:
            print('Timeout while waiting SQS queue to be purged :(')
            raise Exception
    print('SQS queue is purged :)')


def _get_all_queue_messages(sqs_client, queue, expected_messages):
    messages = []

    while len(messages) < expected_messages:
        sqs_messages = sqs_client.receive_message(QueueUrl=queue)
        if 'Messages' in sqs_messages:
            for message in sqs_messages['Messages']:
                if message not in messages:
                    messages.append(message)
                    sqs_client.delete_message(QueueUrl=queue, ReceiptHandle=message['ReceiptHandle'])
        else:
            time.sleep(0.1)
            continue

    return messages


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

## TODO mirar los DLQs a ver que les pasa, si es necesario simular con tests

def _store_test_sra_run(database_holder, srr, sra_project_id):
    database_cursor, database_connection = database_holder

    run_statement = database_cursor.mogrify('insert into sracollector_dev.sra_run (srr, sra_project_id) values (%s, %s) returning id',
                                            (srr, sra_project_id))
    database_cursor.execute(run_statement)
    inserted_sra_run_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_sra_run_id


def _get_customized_input_from_sqs(expected_bodies: [str], function_name: str, suffix: str = None) -> dict:
    fixture_filename = function_name + (suffix if suffix is not None else '') + '_input.json'

    with open(f'tests/fixtures/{fixture_filename}') as json_data:
        payload = json.load(json_data)
        assert len(payload['Records']) == len(expected_bodies), 'Fixture file should contain the same number of empty bodies as the expected_bodies list length'
        for index, record in enumerate(payload['Records']):
            record['body'] = expected_bodies[index]
        return payload
