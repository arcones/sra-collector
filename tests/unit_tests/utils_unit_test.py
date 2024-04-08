import sys
from unittest.mock import Mock

import jaydebeapi
import urllib3

http = urllib3.PoolManager()

DEFAULT_FIXTURE = {
    'query_+300': 'foo AND bar AND baz',
    'query_<20': 'foobar',
    'query_over_limit': 'cancer',
    'mail': 'crispin@grijander.com',
    'results': 384,
    'ncbi_id': 200126815,
    'gse': 'GSE126815',
    'srp': 'SRP185522',
    'srrs': ['SRR22873806', 'SRR22873807'],
    'metadatas': [
        {'spots': 342491658,
         'bases': 101957489026,
         'organism': 'human gammaherpesvirus 4',
         'phred': [(2, 2781953), (11, 3181387515), (25, 5012929637), (37, 93760389921)],
         'statistic_reads': {'nspots': 342491658,
                             'read_0_count': 342491658,
                             'read_0_average': 148.87,
                             'read_0_stdev': 10.29,
                             'read_1_count': 342491658,
                             'read_1_average': 148.83,
                             'read_1_stdev': 10.41,
                             'layout': 'PAIRED'}
         },
        {'spots': 734983,
         'bases': 3000000000,
         'organism': 'drosophila',
         'phred': [(18, 998736778), (30, 938398), (31, 324823), (38, 2000000000), (40, 1)],
         'statistic_reads': {'nspots': 48243,
                             'read_0_count': 26546,
                             'read_0_average': 5654.44,
                             'read_0_stdev': 45646.44,
                             'read_1_count': 0,
                             'read_1_average': 0,
                             'read_1_stdev': 0,
                             'layout': 'SINGLE'}
         }]
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


def store_test_request(database_holder, request_id, ncbi_query, status=None):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into request (id, query, geo_count, mail, status) values (?, ?, ?, ?, ?);',
                            [request_id, ncbi_query, 1, DEFAULT_FIXTURE['mail'], status if status is not None else 'PENDING'])
    database_connection.commit()


def stores_test_ncbi_study(database_holder, request_id, ncbi_id, srr_metadata_count=None):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into ncbi_study (request_id, ncbi_id, srr_metadata_count) values (?, ?, ?);', [request_id, ncbi_id, srr_metadata_count])
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
    database_cursor.execute('insert into sra_project (geo_study_id, srp) values (?,?);', [geo_study_id, srp])
    database_connection.commit()
    database_cursor.execute('select id from sra_project where geo_study_id=? and srp=?;', [geo_study_id, srp])
    return database_cursor.fetchone()[0]


def store_test_sra_run(database_holder, sra_project_id, srr):
    database_connection, database_cursor = database_holder
    database_cursor.execute('insert into sra_run (sra_project_id, srr) values (?, ?);', [sra_project_id, srr])
    database_connection.commit()
    database_cursor.execute('select id from sra_run where sra_project_id=? and srr=?;', [sra_project_id, srr])
    return database_cursor.fetchone()[0]


def store_test_metadata(database_holder, sra_run_ids):
    database_connection, database_cursor = database_holder
    for sra_run_id, metadata in zip(sra_run_ids, DEFAULT_FIXTURE['metadatas']):
        parameters = [sra_run_id, metadata['spots'], metadata['bases'], metadata['organism']]
        database_cursor.execute('insert into sra_run_metadata (sra_run_id, spots, bases, organism) values (?, ?, ?, ?);', parameters)
        database_connection.commit()

        database_cursor.execute('select id from sra_run_metadata where sra_run_id=? and spots=? and bases=? and organism=?;', parameters)
        sra_run_metadata_id = database_cursor.fetchone()[0]

        statistic_read_parameters = [sra_run_metadata_id, metadata['statistic_reads']['nspots'], metadata['statistic_reads']['layout'],
                                     metadata['statistic_reads']['read_0_count'], metadata['statistic_reads']['read_0_average'], metadata['statistic_reads']['read_0_stdev'],
                                     metadata['statistic_reads']['read_1_count'], metadata['statistic_reads']['read_1_average'], metadata['statistic_reads']['read_1_stdev']]
        database_cursor.execute('insert into sra_run_metadata_statistic_read (sra_run_metadata_id, nspots, layout, '
                                'read_0_count, read_0_average, read_0_stdev, read_1_count, read_1_average, read_1_stdev) '
                                'values (?, ?, ?, ?, ?, ?, ?, ?, ?);', statistic_read_parameters)
        database_connection.commit()

        for phred_item in metadata['phred']:
            database_cursor.execute('insert into sra_run_metadata_phred (sra_run_metadata_id, score, read_count) values (?, ?, ?);',
                                    [sra_run_metadata_id, phred_item[0], phred_item[1]])
            database_connection.commit()


def mock_eutils(method, url, *args, **kwargs):
    eutils_base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'

    if method == 'GET':
        if url == f"{eutils_base_url}/esearch.fcgi?db=gds&retmode=json&term={DEFAULT_FIXTURE['query_+300']}&retmax=1":
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
        elif url == f'https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/run_new?acc=SRR6348099':
            with open('tests/fixtures/G_get_srr_metadata_problematic_1.xml') as response:
                return Mock(data=response.read())
        elif url == f'https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/run_new?acc=SRR10522811':
            with open('tests/fixtures/G_get_srr_metadata_problematic_2.xml') as response:
                return Mock(data=response.read())
        elif url == f'https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/run_new?acc=SRR23100522':
            with open('tests/fixtures/G_get_srr_metadata_problematic_3.xml') as response:
                return Mock(data=response.read())
        else:
            sys.exit(f'Cannot mock unexpected call to eutils with url {url}')
    else:
        sys.exit(f'Cannot mock unexpected call to eutils with method {method}')


def mock_pysradb(entity, *args, **kwargs):
    if entity == 'GSE126183':
        return {'study_accession': ['SRP184257']}
    elif entity.startswith('GSE'):
        return {'study_accession': [DEFAULT_FIXTURE['srp']]}
    elif entity.startswith('SRP'):
        return {'run_accession': DEFAULT_FIXTURE['srrs']}
    else:
        sys.exit(f'Cannot mock unexpected call to pysradb with entity {entity}')
