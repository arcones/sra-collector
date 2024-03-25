import sys
from unittest.mock import Mock

import jaydebeapi
import urllib3

http = urllib3.PoolManager()

DEFAULT_FIXTURE = {
    'query_+500': 'cancer AND mus musculus AND children',
    'query_<20': 'rna seq and homo sapiens and myeloid and leukemia',
    'query_over_limit': 'cancer',
    'results': 687,
    'ncbi_id': 200126815,
    'gse': 'GSE126815',
    'srp': 'SRP185522',
    'srrs': ['SRR22873806', 'SRR22873807'],
    'metadata': {'spots': 342491658,
                 'bases': 101957489026,
                 'layout': 'SINGLE',
                 'organism': 'human gammaherpesvirus 4',
                 'phred': [(2, 2781953), (11, 3181387515), (25, 5012929637), (37, 93760389921)],
                 'statistic_reads': {'nspots': 342491658,
                                     'reads': [(0, 342491658, 148.87, 10.29),
                                               (1, 342491658, 148.83, 10.41)]}}
}


class Context:
    def __init__(self, function_name: str):
        self.function_name = function_name


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


def store_test_request(database_holder, request_id, ncbi_query):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into request (id, query, geo_count) values (?, ?, ?);', [request_id, ncbi_query, 1])
    database_connection.commit()


def stores_test_ncbi_study(database_holder, request_id, ncbi_id):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into ncbi_study (request_id, ncbi_id) values (?, ?);', [request_id, ncbi_id])
    database_connection.commit()
    database_cursor.execute('select id from ncbi_study where request_id=? and ncbi_id=?', [request_id, ncbi_id])
    return database_cursor.fetchone()[0]


def store_test_geo_study(database_holder, study_id, gse):
    database_connection, database_cursor = database_holder

    database_cursor.execute('insert into geo_study (ncbi_study_id, gse) values (?, ?);', [study_id, gse])
    database_connection.commit()
    database_cursor.execute('select id from geo_study where ncbi_study_id=? and gse=?', [study_id, gse])
    return database_cursor.fetchone()[0]


def store_test_sra_project(database_holder, geo_study_id, srp):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into sra_project (srp) values (?);', [srp])
    database_connection.commit()
    database_cursor.execute('select max(id) from sra_project where srp=?;', [srp])
    inserted_sra_project_id = database_cursor.fetchone()[0]
    database_cursor.execute('insert into geo_study_sra_project_link (geo_study_id, sra_project_id) values (?, ?);', [geo_study_id, inserted_sra_project_id])
    database_connection.commit()
    return inserted_sra_project_id


def store_test_sra_run(database_holder, sra_project_id, srr):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into sra_run (sra_project_id, srr) values (?, ?);', [sra_project_id, srr])
    database_connection.commit()
    database_cursor.execute('select id from sra_run where sra_project_id=? and srr=?;', [sra_project_id, srr])
    return database_cursor.fetchone()[0]


def check_link_and_srp_rows(database_holder, ncbi_study_ids, srp):
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


def mock_eutils(method, url, *args, **kwargs):
    eutils_base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'

    if method == 'GET':
        if url == f"{eutils_base_url}/esearch.fcgi?db=gds&retmode=json&term={DEFAULT_FIXTURE['query_+500']}&retmax=1":
            with open('tests/fixtures/B_get_query_pages_mock_esearch.json') as response:
                return Mock(data=response.read())
        if url == f"{eutils_base_url}/esearch.fcgi?db=gds&retmode=json&term={DEFAULT_FIXTURE['query_over_limit']}&retmax=1":
            with open('tests/fixtures/B_get_query_pages_mock_esearch_over_limit.json') as response:
                return Mock(data=response.read())
        elif url == f"{eutils_base_url}/esearch.fcgi?db=gds&retmode=json&term={DEFAULT_FIXTURE['query_<20']}&retmax=500&retstart=0&usehistory=y":
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
        elif url == f"https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/run_new?acc={DEFAULT_FIXTURE['srrs'][0]}":
            with open('tests/fixtures/G_get_srr_metadata.xml') as response:
                return Mock(data=response.read())
        else:
            sys.exit(f'Cannot mock unexpected call to eutils with url {url}')
    else:
        sys.exit(f'Cannot mock unexpected call to eutils with method {method}')


def mock_pysradb(entity, *args, **kwargs):
    if entity.startswith('GSE'):
        return {'study_accession': [DEFAULT_FIXTURE['srp']]}
    elif entity.startswith('SRP'):
        return {'run_accession': DEFAULT_FIXTURE['srrs']}
    else:
        sys.exit(f'Cannot mock unexpected call to pysradb with entity {entity}')
