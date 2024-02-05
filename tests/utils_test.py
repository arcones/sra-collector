import json
import random
import string
import time

import boto3
import psycopg2
import urllib3

http = urllib3.PoolManager()

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits


def _print_test_params(lambda_function: str, params: str) -> None:
    print(f'\nIn {lambda_function} test were used: {params}')


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
                time.sleep(5)
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
            time.sleep(5)
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


def _store_test_request(database_holder, expected_request_id, ncbi_query):
    database_cursor, database_connection = database_holder

    request_statement = database_cursor.mogrify(f'insert into sracollector_dev.request (id, query, geo_count) values (%s, %s, %s)', (expected_request_id, ncbi_query, 1))
    database_cursor.execute(request_statement)
    database_connection.commit()


def _store_test_study(database_holder, expected_study_id, expected_request_id, expected_gse):
    database_cursor, database_connection = database_holder

    study_statement = database_cursor.mogrify(f'insert into sracollector_dev.geo_study (ncbi_id, request_id, gse) values (%s, %s, %s) returning id',
                                              (expected_study_id, expected_request_id, expected_gse))
    database_cursor.execute(study_statement)
    inserted_geo_study_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_geo_study_id


def _store_test_srp(database_holder, expected_srp, inserted_geo_study_id):
    database_cursor, database_connection = database_holder

    project_statement = database_cursor.mogrify(f'insert into sracollector_dev.sra_project (srp, geo_study_id) values (%s, %s) returning id',
                                                (expected_srp, inserted_geo_study_id))
    database_cursor.execute(project_statement)
    inserted_sra_project_id = database_cursor.fetchone()[0]
    database_connection.commit()
    return inserted_sra_project_id


def _get_customized_input_from_sqs(function_name: str, expected_body: str) -> dict:
    with open(f'tests/fixtures/{function_name}_input.json') as json_data:
        payload = json.load(json_data)
        payload['Records'][0]['body'] = expected_body
        return payload
