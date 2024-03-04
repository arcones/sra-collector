import json
import logging
from enum import Enum

import boto3
import urllib3
from postgres_connection import postgres_connection

boto3.set_stream_logger(name='botocore.credentials', level=logging.ERROR)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)
logger = logging.getLogger(__name__)
FORMAT = '%(funcName)s %(message)s'

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')
output_sqs = 'https://sqs.eu-central-1.amazonaws.com/120715685161/D_geos'

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
    if event:
        logging.info(f'Received {len(event["Records"])} records event {event}')
        ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key_secret')
        ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

        ordered_records = sorted(event['Records'], key=lambda r: json.loads(r['body'])['study_id'])

        request_id_2_study_id_list = []

        for record in ordered_records:
            try:
                request_body = json.loads(record['body'])

                logging.info(f'Processing record {request_body}')

                request_id = request_body['request_id']
                study_id = request_body['study_id']
                request_id_2_study_id_list.append({'request_id': request_id, 'study_id': str(study_id)})
            except Exception as exception:
                logging.error(f'An exception has occurred: {str(exception)}')
                raise exception

        base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'
        response = http.request('GET', f'{base_url}&id={",".join(request_id_2_study_id["study_id"] for request_id_2_study_id in request_id_2_study_id_list)}')
        parsed_response = json.loads(response.data)['result']

        for study_id_in_response in parsed_response:
            request_id_2_study_id = [request_id_2_study_id for request_id_2_study_id in request_id_2_study_id_list if request_id_2_study_id['study_id'] == study_id_in_response]
            if len(request_id_2_study_id) == 1 and study_id_in_response == request_id_2_study_id[0]['study_id']:
                summary_process(request_id_2_study_id[0]['request_id'], int(study_id_in_response), parsed_response[study_id_in_response])


def summary_process(request_id: str, study_id: int, summary: str):
    try:
        logging.debug(f'Study summary from study {study_id} is {summary}')
        geo_entity = extract_geo_entity_from_summaries(summary)

        if geo_entity is not None:
            logging.info(f'Retrieved geo {geo_entity.identifier} for study {study_id}')
            store_geo_entity_in_db(request_id, study_id, geo_entity)

            if geo_entity.geo_entity_type is GeoEntityType.GSE:
                message = {'request_id': request_id, 'gse': geo_entity.identifier}
                sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(message))
                logging.info(f'Sent message {message} for study {study_id}')
        else:
            logging.info(f'The record with request_id {request_id} and study_id {study_id} has already been processed')
    except Exception as exception:
        if exception is not SystemError:
            logging.error(f'An exception has occurred: {str(exception)}')
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
            logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def get_id_ncbi_study(request_id: str, study_id: int) -> int:
    try:
        statement = f'select id from ncbi_study where request_id=%s and ncbi_id=%s;'
        parameters = (request_id, study_id)
        return postgres_connection.execute_read_statement_for_primary_key(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def store_geo_entity_in_db(request_id: str, study_id: int, geo_entity: GeoEntity):
    try:
        ncbi_id = get_id_ncbi_study(request_id, study_id)
        statement = f"""insert into {geo_entity.geo_entity_type.value['table']}
                        (ncbi_study_id, {geo_entity.geo_entity_type.value['short_name']})
                        values (%s, %s) on conflict
                        (ncbi_study_id, {geo_entity.geo_entity_type.value['short_name']}) do nothing;"""
        parameters = (ncbi_id, geo_entity.identifier)
        postgres_connection.execute_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
