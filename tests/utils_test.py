import random
import string
import sys
from unittest.mock import Mock

import jaydebeapi
import urllib3

http = urllib3.PoolManager()

CHARACTERS = string.ascii_uppercase + string.ascii_lowercase + string.digits
DEFAULT_FIXTURE = {'query': 'rna seq and homo sapiens and myeloid and leukemia', 'results': 1096, 'ncbi_id': 200126815, 'gse': 'GSE126815', 'srp': 'SRP185522',
                   'srrs': ['SRR22873806', 'SRR22873807']}


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


def _check_link_and_srp_rows(database_holder, ncbi_study_ids, srp):
    _, database_cursor = database_holder
    ncbi_study_ids_for_sql_in = ', '.join([f'{ncbi_study_id}' for ncbi_study_id in ncbi_study_ids])
    database_cursor.execute(f"""select count(*) from geo_study_sra_project_link
                                join geo_study on geo_study_id = id
                                where ncbi_study_id in ({ncbi_study_ids_for_sql_in})""")
    link_rows = database_cursor.fetchone()[0]
    database_cursor.execute(f"""select count(distinct sp.id) from sra_project sp
                                join geo_study_sra_project_link gsspl on gsspl.sra_project_id = sp.id
                                join geo_study gs on gsspl.geo_study_id = gs.id
                                where srp='{srp}' and ncbi_study_id in ({ncbi_study_ids_for_sql_in})""")
    srp_rows = database_cursor.fetchone()[0]
    return link_rows, srp_rows


def _mock_eutils(method, url, *args, **kwargs):
    eutils_base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'

    if method == 'GET':
        if url == f'{eutils_base_url}/esearch.fcgi?db=gds&retmode=json&term=rna seq and homo sapiens and myeloid and leukemia&retmax=1':
            with open('tests/fixtures/B_get_query_pages_mock_esearch.json') as response:
                return Mock(data=response.read())
        elif url == f'{eutils_base_url}/esearch.fcgi?db=gds&retmode=json&term=rna seq and homo sapiens and myeloid and leukemia&retmax=500&retstart=0&usehistory=y':
            with open('tests/fixtures/C_get_study_ids_mocked_esearch.json') as response:
                return Mock(data=response.read())
        elif url == f'{eutils_base_url}/esummary.fcgi?db=gds&retmode=json&api_key=mockedSecret&id=200126815':
            with open('tests/fixtures/D_get_study_geo_mocked_esummary_gse.json') as response:
                return Mock(data=response.read())
        elif url == f'{eutils_base_url}/esummary.fcgi?db=gds&retmode=json&api_key=mockedSecret&id=100019750':
            with open('tests/fixtures/D_get_study_geo_mocked_esummary_gpl.json') as response:
                return Mock(data=response.read())
        elif url == f'{eutils_base_url}/esummary.fcgi?db=gds&retmode=json&api_key=mockedSecret&id=3268':
            with open('tests/fixtures/D_get_study_geo_mocked_esummary_gds.json') as response:
                return Mock(data=response.read())
        elif url == f'{eutils_base_url}/esummary.fcgi?db=gds&retmode=json&api_key=mockedSecret&id=305668979':
            with open('tests/fixtures/D_get_study_geo_mocked_esummary_gsm.json') as response:
                return Mock(data=response.read())
        else:
            sys.exit(f'Cannot mock unexpected call to eutils with url {url}')
    else:
        sys.exit(f'Cannot mock unexpected call to eutils with method {method}')


def _mock_pysradb(entity, *args, **kwargs):
    if entity.startswith('GSE'):
        return {'study_accession': [DEFAULT_FIXTURE['srp']]}
    elif entity.startswith('SRP'):
        return {'run_accession': DEFAULT_FIXTURE['srrs']}
    else:
        sys.exit(f'Cannot mock unexpected call to pysradb with entity {entity}')
