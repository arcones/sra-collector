import json
import logging
import xml.etree.ElementTree as ET
from enum import Enum

import boto3
import urllib3
from db_connection.db_connection import DBConnectionManager
from sqs_helper.sqs_helper import SQSHelper

http = urllib3.PoolManager()

sqs = boto3.client('sqs', region_name='eu-central-1')


class Read:
    def __init__(self, index: int, count: int, average: float, stdev: float):
        self.index = index
        self.count = count
        self.average = average
        self.stdev = stdev


class StatisticRead:
    def __init__(self, spots: int, reads: [Read]):
        self.spots = spots
        self.reads = reads


class Layout(Enum):
    PAIRED = 'PAIRED'
    SINGLE = 'SINGLE'


class SRRMetadata:  # TODO sample type: wild type, etc
    def __init__(self, srr: str):
        self.srr = srr
        self.spots = None
        self.bases = None
        self.phred = None
        self.statistic_read = None
        self.layout = None
        self.organism = None

    def set_spots(self, spots: int):
        self.spots = spots

    def set_bases(self, bases: int):
        self.bases = bases

    def set_phred(self, phred: dict):
        self.phred = phred

    def set_statistic_read(self, statistic_read: StatisticRead):
        self.statistic_read = statistic_read

    def set_layout(self, layout: Layout):
        self.layout = layout

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
                    srr = get_srr_sra_run(database_holder, sra_run_id)
                    srr_metadata = get_srr_metadata(srr)
                    srr_metadata_id = store_srr_metadata_in_db(database_holder, sra_run_id, srr_metadata)
                    SQSHelper(sqs, context.function_name).send(message_bodies={'srr_metadata_id': srr_metadata_id})
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')

        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def store_srr_metadata_in_db(database_holder, sra_run_id: int, srr_metadata: SRRMetadata):
    try:
        sra_run_metadata_id = database_holder.execute_write_statement('insert into sra_run_metadata (sra_run_id, spots, bases, layout, organism) '
                                                                      'values (%s, %s, %s, %s, %s) on conflict do nothing returning id;',
                                                                      sra_run_id, srr_metadata.spots, srr_metadata.bases, srr_metadata.layout, srr_metadata.layout)
        store_srr_metadata_phred(database_holder, sra_run_metadata_id, srr_metadata.phred)
        store_srr_statistic_reads(database_holder, sra_run_metadata_id, srr_metadata.statistic_read)
        return sra_run_metadata_id
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srr_metadata_in_db.__name__}: {str(exception)}')
        raise exception


def store_srr_metadata_phred(database_holder, sra_run_metadata_id: int, phred: dict):
    try:
        phred_and_sra_run_metadata_id_tuples = [(sra_run_metadata_id, score, read_count) for score, read_count in phred]
        return database_holder.execute_bulk_write_statement('insert into sra_run_metadata_phred (sra_run_metadata_id, score, read_count) '
                                                            'values (%s, %s, %s) on conflict do nothing returning id;',
                                                            phred_and_sra_run_metadata_id_tuples)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srr_metadata_phred.__name__}: {str(exception)}')
        raise exception


def store_srr_statistic_reads(database_holder, sra_run_metadata_id: int, statistic_read: StatisticRead):
    try:
        sra_run_metadata_statistic_read_id = database_holder.execute_write_statement('insert into sra_run_metadata_statistic_read (sra_run_metadata_id, nspots) '
                                                                                     'values (%s, %s) on conflict do nothing returning id;',
                                                                                     sra_run_metadata_id, statistic_read.spots)
        store_srr_read(database_holder, sra_run_metadata_statistic_read_id, statistic_read.reads)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srr_metadata_phred.__name__}: {str(exception)}')
        raise exception


def store_srr_read(database_holder, sra_run_metadata_statistic_read_id: int, reads: [Read]):
    try:
        read_and_sra_run_metadata_statistic_read_id_tuples = [(sra_run_metadata_statistic_read_id, read.index, read.count, read.average, read.stdev) for read in reads]
        return database_holder.execute_bulk_write_statement('insert into sra_run_metadata_read (sra_run_metadata_statistic_read_id, index, count, average, stdev)'
                                                            'values (%s, %s, %s, %s, %s) on conflict do nothing returning id;',
                                                            read_and_sra_run_metadata_statistic_read_id_tuples)
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_srr_metadata_phred.__name__}: {str(exception)}')
        raise exception


def get_srr_sra_run(database_holder, sra_run_id: int) -> str:
    try:
        statement = f'select srr from sra_run where id=%s'
        parameters = (sra_run_id,)
        row = database_holder.execute_read_statement(statement, parameters)
        return row[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_srr_sra_run.__name__}: {str(exception)}')
        raise exception


def get_srr_metadata(srr: str) -> SRRMetadata:
    try:
        srr_metadata = SRRMetadata(srr)

        url = f'https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/run_new?acc={srr_metadata.srr}'
        response = http.request('GET', url).data
        root = ET.fromstring(response)

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
            reads = []
            for read_element in statistics_element:
                index = int(read_element.get('index'))
                count = int(read_element.get('count'))
                average = float(read_element.get('average'))
                stdev = float(read_element.get('stdev'))

                reads.append(Read(index, count, average, stdev))

            nspots = int(statistics_element.get('nspots')) if statistics_element.get('nspots') is not None and statistics_element.get('nspots').isdigit() else None
            statistic_read = StatisticRead(nspots, reads)

            srr_metadata.set_statistic_read(statistic_read)

        member_node = root.findall('.//RUN/Pool/Member')
        if len(member_node) > 0:
            member_element = member_node[0]
            srr_metadata.set_organism(member_element.get('organism'))

        if root.find('.//EXPERIMENT/DESIGN/LIBRARY_DESCRIPTOR/LIBRARY_LAYOUT/PAIRED') is not None:
            srr_metadata.set_layout(Layout('PAIRED'))
        elif root.find('.//EXPERIMENT/DESIGN/LIBRARY_DESCRIPTOR/LIBRARY_LAYOUT/SINGLE') is not None:
            srr_metadata.set_layout(Layout('SINGLE'))

        return srr_metadata
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_srr_metadata.__name__}: {str(exception)}')
        raise exception
