import inspect
import json
import logging
from enum import Enum

import boto3
import urllib3
from db_connection.db_connection import DBConnectionManager
from sqs_helper.sqs_helper import SQSHelper

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)
logger = logging.getLogger(__name__)
FORMAT = '%(funcName)s %(message)s'

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')

all_http_codes_but_200 = list(range(100, 200)) + list(range(300, 600))
retries = urllib3.Retry(status_forcelist=all_http_codes_but_200, backoff_factor=0.5)
http = urllib3.PoolManager(retries=retries)


class GeoEntityType(Enum):
    GSE = {'table': 'geo_study', 'short_name': 'gse'}
    GSM = {'table': 'geo_experiment', 'short_name': 'gsm'}
    GPL = {'table': 'geo_platform', 'short_name': 'gpl'}
    GDS = {'table': 'geo_data_set', 'short_name': 'gds'}


class GeoEntity:
    def __init__(self, identifier: str):
        self.identifier = identifier.upper()
        self.geo_entity_type = self.set_type()

    def set_type(self):
        if self.identifier.startswith('GSE'):
            return GeoEntityType.GSE
        elif self.identifier.startswith('GSM'):
            return GeoEntityType.GSM
        elif self.identifier.startswith('GPL'):
            return GeoEntityType.GPL
        elif self.identifier.startswith('GDS'):
            return GeoEntityType.GDS
        else:
            raise ValueError(f'Unknown identifier prefix: {self.identifier}')


def handler(event, context):
    with DBConnectionManager() as database_holder:
        if event:
            logging.info(f'Received {len(event["Records"])} records event {event}')
            ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key_secret')
            ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

            ncbi_study_id_2_ncbi_id_list = []

            for record in event['Records']:
                try:
                    request_body = json.loads(record['body'])

                    logging.info(f'Processing record {request_body}')

                    ncbi_study_id = request_body['ncbi_study_id']
                    ncbi_study_id_2_ncbi_id_list.append({'ncbi_study_id': ncbi_study_id, 'ncbi_id': get_ncbi_id(database_holder, ncbi_study_id)})
                except Exception as exception:
                    logging.error(f'An exception has occurred in {handler.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
                    raise exception

            base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'
            ncbi_ids_as_strs = list(map(str, [ncbi_study_id_2_ncbi_id['ncbi_id'] for ncbi_study_id_2_ncbi_id in ncbi_study_id_2_ncbi_id_list]))
            response = http.request('GET', f'{base_url}&id={",".join(ncbi_ids_as_strs)}')
            parsed_response = json.loads(response.data)['result']

            for parsed_response_item in parsed_response:
                if parsed_response_item in ncbi_ids_as_strs:
                    ncbi_id_2_study_id = [ncbi_id_2_study_id for ncbi_id_2_study_id in ncbi_study_id_2_ncbi_id_list if str(ncbi_id_2_study_id['ncbi_id']) == parsed_response_item][
                        0]
                    summary_process(database_holder, context.function_name, ncbi_id_2_study_id['ncbi_study_id'], int(parsed_response_item), parsed_response[parsed_response_item])


def summary_process(database_holder, function_name: str, ncbi_study_id: int, ncbi_id: int, summary: str):
    try:
        logging.debug(f'Study summary from study {ncbi_id} is {summary}')
        geo_entity = extract_geo_entity_from_summaries(summary)

        if geo_entity is not None:
            logging.info(f'Retrieved geo {geo_entity.identifier} for study {ncbi_id}')
            geo_entity_id = store_geo_entity_in_db(database_holder, ncbi_study_id, geo_entity)

            if geo_entity.geo_entity_type is GeoEntityType.GSE:
                message_body = {'geo_entity_id': geo_entity_id}
                SQSHelper(function_name, sqs).send(message_body=message_body)
        else:
            logging.info(f'The record ncbi_study_id {ncbi_study_id} and study_id {ncbi_id} has already been processed')
    except Exception as exception:
        if exception is not SystemError:
            logging.error(f'An exception has occurred in {summary_process.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception


def extract_geo_entity_from_summaries(summary: str) -> GeoEntity:
    try:
        logging.info(f'Extracting GEO from {summary}')
        if summary['entrytype'].upper() in [entity.value['short_name'].upper() for entity in GeoEntityType]:
            geo_entity = GeoEntity(summary['accession'])
            logging.info(f'Extracted GEO entity {geo_entity.identifier}')
            return geo_entity
        else:
            message = f'For summary {summary} there are none GEO entity'
            logging.warning(message)
    except Exception as exception:
        if exception is not ValueError:
            logging.error(f'An exception has occurred in {extract_geo_entity_from_summaries.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception


def get_ncbi_id(database_holder, ncbi_study_id: int) -> int:
    try:
        statement = f'select ncbi_id from ncbi_study where id=%s;'
        parameters = (ncbi_study_id,)
        return database_holder.execute_read_statement(statement, parameters)[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_ncbi_id.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception


def store_geo_entity_in_db(database_holder, ncbi_study_id: int, geo_entity: GeoEntity):
    try:
        statement = f"""insert into {geo_entity.geo_entity_type.value['table']}
                        (ncbi_study_id, {geo_entity.geo_entity_type.value['short_name']})
                        values (%s, %s) on conflict do nothing returning id;"""
        parameters = (ncbi_study_id, geo_entity.identifier)
        return database_holder.execute_write_statement(statement, parameters)[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {store_geo_entity_in_db.__name__} line {inspect.currentframe().f_lineno}: {str(exception)}')
        raise exception
