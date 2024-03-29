import json
import logging
import xml.etree.ElementTree as ElementTree

import boto3
import urllib3
from db_connection.db_connection import DBConnectionManager
from sqs_helper.sqs_helper import SQSHelper

http = urllib3.PoolManager()

sqs = boto3.client('sqs', region_name='eu-central-1')


class StatisticRead:
    def __init__(self, nspots: int, read_0_count: int, read_0_average: float, read_0_stdev: float, read_1_count: int, read_1_average: float, read_1_stdev: float):
        self.nspots = nspots
        self.read_0_count = read_0_count
        self.read_0_average = read_0_average
        self.read_0_stdev = read_0_stdev
        self.read_1_count = read_1_count
        self.read_1_average = read_1_average
        self.read_1_stdev = read_1_stdev
        self.layout = self.set_layout()

    def set_layout(self):
        if self.read_0_count > 0 and self.read_1_count > 0:
            return 'PAIRED'
        elif self.read_0_count > 0 or self.read_1_count > 0:
            return 'SINGLE'


class SRRMetadata:  # TODO sample type: wild type, etc
    def __init__(self, srr: str):
        self.srr = srr
        self.spots = None
        self.bases = None
        self.phred = None
        self.statistic_read = None
        self.organism = None

    def set_spots(self, spots: int):
        self.spots = spots

    def set_bases(self, bases: int):
        self.bases = bases

    def set_phred(self, phred: dict):
        self.phred = phred

    def set_statistic_read(self, statistic_read: StatisticRead):
        self.statistic_read = statistic_read

    def set_organism(self, organism: str):
        self.organism = organism


def handler(event, context):
    if event:
        logging.info(f'Received {len(event["Records"])} records event {event}')

        batch_item_failures = []
        sqs_batch_response = {}

        for record in event['Records']:
            try:
                with DBConnectionManager() as database_holder:
                    request_body = json.loads(record['body'])

                    logging.info(f'Processing record {request_body}')

                    sra_run_id = request_body['sra_run_id']
                    request_id, srr = get_request_id_and_srr(database_holder, sra_run_id)
                    srr_metadata = get_srr_metadata(srr)

                    store_srr_metadata_in_db(database_holder, sra_run_id, srr_metadata)

                    if is_srr_metadata_count_ready(database_holder, request_id):
                        expected_srr_metadatas = get_sum_srr_count_metadata(database_holder, request_id)
                        actual_srr_metadatas = get_sum_actual_metadatas(database_holder, request_id)

                        if expected_srr_metadatas == actual_srr_metadatas:
                            SQSHelper(sqs, context.function_name).send(message_body={'request_id': request_id})
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')

        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def store_srr_metadata_in_db(database_holder, sra_run_id: int, srr_metadata: SRRMetadata):
    try:
        sra_run_metadata_id = database_holder.execute_write_statement('insert into sra_run_metadata (sra_run_id, spots, bases, organism) '
                                                                      'values (%s, %s, %s, %s) on conflict do nothing returning id;',
                                                                      (sra_run_id, srr_metadata.spots, srr_metadata.bases, srr_metadata.organism))[0][0]
        store_srr_metadata_phred(database_holder, sra_run_metadata_id, srr_metadata.phred)
        store_srr_statistic_reads(database_holder, sra_run_metadata_id, srr_metadata.statistic_read)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srr_metadata_in_db.__name__}: {str(exception)}')
        raise exception


def store_srr_metadata_phred(database_holder, sra_run_metadata_id: int, phred: dict):
    try:
        phred_and_sra_run_metadata_id_tuples = [(sra_run_metadata_id, score, read_count) for score, read_count in phred.items()]
        return database_holder.execute_bulk_write_statement('insert into sra_run_metadata_phred (sra_run_metadata_id, score, read_count) '
                                                            'values (%s, %s, %s) on conflict do nothing returning id;',
                                                            phred_and_sra_run_metadata_id_tuples)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srr_metadata_phred.__name__}: {str(exception)}')
        raise exception


def store_srr_statistic_reads(database_holder, sra_run_metadata_id: int, statistic_read: StatisticRead):
    try:
        statement = ('insert into sra_run_metadata_statistic_read '
                     '(sra_run_metadata_id, nspots, layout, read_0_count, read_0_average, read_0_stdev, read_1_count, read_1_average, read_1_stdev) '
                     'values (%s, %s, %s, %s, %s, %s, %s, %s, %s) on conflict do nothing returning id;')
        parameters = (sra_run_metadata_id, statistic_read.nspots, statistic_read.layout, statistic_read.read_0_count, statistic_read.read_0_average,
                      statistic_read.read_0_stdev, statistic_read.read_1_count, statistic_read.read_1_average, statistic_read.read_1_stdev)
        sra_run_metadata_statistic_read_id = database_holder.execute_write_statement(statement, parameters)[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srr_statistic_reads.__name__}: {str(exception)}')
        raise exception


def get_request_id_and_srr(database_holder, sra_run_id: int) -> (str, str):
    try:
        statement = ('select r.id, sr.srr from request r '
                     'join ncbi_study ns on r.id = ns.request_id '
                     'join geo_study gs on ns.id = gs.ncbi_study_id '
                     'join sra_project sp on gs.id = sp.geo_study_id '
                     'join sra_run sr on sp.id = sr.sra_project_id '
                     'where sr.id=%s;')
        parameters = (sra_run_id,)
        return database_holder.execute_read_statement(statement, parameters)[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_request_id_and_srr.__name__}: {str(exception)}')
        raise exception


def get_srr_metadata(srr: str) -> SRRMetadata:
    try:
        srr_metadata = SRRMetadata(srr)

        url = f'https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/run_new?acc={srr_metadata.srr}'
        response = http.request('GET', url).data
        root = ElementTree.fromstring(response)

        run_node = root.findall('.//RUN')
        if len(run_node) > 0:
            run_element = run_node[0]
            spots = run_element.get('total_spots')
            bases = run_element.get('total_bases')
            if spots is not None and spots.isdigit():
                srr_metadata.set_spots(int(spots))
            if bases is not None and bases.isdigit():
                srr_metadata.set_bases(int(bases))

        quality_count_node = root.findall('.//RUN/QualityCount')
        if len(quality_count_node) > 0:
            quality_count_element = quality_count_node[0]
            phred = {}
            for quality_element in quality_count_element:
                phred[int(quality_element.get('value'))] = int(quality_element.get('count'))

            srr_metadata.set_phred(phred)

        statistics_node = root.findall('.//RUN/Statistics')
        if len(statistics_node) > 0:
            statistics_element = root.findall('.//RUN/Statistics')[0]

            read_0_count = 0
            read_0_average = 0
            read_0_stdev = 0
            read_1_count = 0
            read_1_average = 0
            read_1_stdev = 0

            for read_element in statistics_element:
                if int(read_element.get('index')) == 0:
                    read_0_count = int(read_element.get('count'))
                    read_0_average = float(read_element.get('average'))
                    read_0_stdev = float(read_element.get('stdev'))
                elif int(read_element.get('index')) == 1:
                    read_1_count = int(read_element.get('count'))
                    read_1_average = float(read_element.get('average'))
                    read_1_stdev = float(read_element.get('stdev'))

            nspots = int(statistics_element.get('nspots')) if statistics_element.get('nspots') is not None and statistics_element.get('nspots').isdigit() else None
            statistic_read = StatisticRead(nspots, read_0_count, read_0_average, read_0_stdev, read_1_count, read_1_average, read_1_stdev)

            srr_metadata.set_statistic_read(statistic_read)

        member_node = root.findall('.//RUN/Pool/Member')
        if len(member_node) > 0:
            member_element = member_node[0]
            srr_metadata.set_organism(member_element.get('organism'))

        return srr_metadata
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_srr_metadata.__name__}: {str(exception)}')
        raise exception


def is_srr_metadata_count_ready(database_holder, request_id: str) -> bool:
    try:
        statement = ('select 1 from ncbi_study ns '
                     'join request r on r.id = ns.request_id '
                     'where r.id=%s and srr_metadata_count is null;')
        return not database_holder.execute_read_statement(statement, (request_id,))
    except Exception as exception:
        logging.error(f'An exception has occurred in {is_srr_metadata_count_ready.__name__}: {str(exception)}')
        raise exception


def get_sum_srr_count_metadata(database_holder, request_id: str) -> bool:
    try:
        statement = ('select sum(srr_metadata_count) from ncbi_study ns '
                     'join request r on r.id = ns.request_id '
                     'where r.id=%s;')
        return not database_holder.execute_read_statement(statement, (request_id,))[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_sum_srr_count_metadata.__name__}: {str(exception)}')
        raise exception


def get_sum_actual_metadatas(database_holder, request_id: str) -> bool:
    try:
        statement = ('select count(srm.id) from sra_run_metadata srm '
                     'join sra_run sr on sr.id = srm.sra_run_id '
                     'join sra_project sp on sp.id = sr.sra_project_id '
                     'join geo_study gs on gs.id = sp.geo_study_id '
                     'join ncbi_study ns on ns.id = gs.ncbi_study_id '
                     'join request r on r.id = ns.request_id '
                     'where r.id=%s;')
        return not database_holder.execute_read_statement(statement, (request_id,))[0][0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_sum_actual_metadatas.__name__}: {str(exception)}')
        raise exception
