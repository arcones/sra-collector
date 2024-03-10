import os
import random
import string

import jaydebeapi
import urllib3

http = urllib3.PoolManager()

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits


def _provide_random_request_id():
    return ''.join(random.choice(CHARACTERS) for char in range(20))


class H2ConnectionManager:
    def __init__(self):
        self.url = 'jdbc:h2:./tmp/test-db/test.db;MODE=PostgreSQL'
        self.jar_path = './db/h2-2.2.224.jar'
        self.driver = 'org.h2.Driver'
        self.credentials = ['', '']

    def __enter__(self):
        self.database_connection = jaydebeapi.connect(self.driver, self.url, self.credentials, self.jar_path)
        self.database_cursor = self.database_connection.cursor()
        return self.database_connection, self.database_cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.database_cursor:
            self.database_cursor.close()
        if self.database_connection:
            self.database_connection.close()


def _store_test_request(database_holder, request_id, ncbi_query):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into request (id, query, geo_count) values (?, ?, ?);', [request_id, ncbi_query, 1])
    database_connection.commit()


def _stores_test_ncbi_study(database_holder, request_id, ncbi_id):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into ncbi_study (request_id, ncbi_id) values (?, ?);', [request_id, ncbi_id])
    database_connection.commit()
    database_cursor.execute('select id from ncbi_study where request_id=? and ncbi_id=?', [request_id, ncbi_id])
    return database_cursor.fetchone()[0]


def _store_test_geo_study(database_holder, study_id, gse):
    database_connection, database_cursor = database_holder

    database_cursor.execute('insert into geo_study (ncbi_study_id, gse) values (?, ?);', [study_id, gse])
    database_connection.commit()
    database_cursor.execute('select id from geo_study where ncbi_study_id=? and gse=?', [study_id, gse])
    return database_cursor.fetchone()[0]


def _store_test_sra_project(database_holder, geo_study_id, srp):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into sra_project (srp) values (?);', [srp])
    database_connection.commit()
    database_cursor.execute('select max(id) from sra_project where srp=?;', [srp])
    inserted_sra_project_id = database_cursor.fetchone()[0]
    database_cursor.execute('insert into geo_study_sra_project_link (geo_study_id, sra_project_id) values (?, ?);', [geo_study_id, inserted_sra_project_id])
    database_connection.commit()
    return inserted_sra_project_id


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
