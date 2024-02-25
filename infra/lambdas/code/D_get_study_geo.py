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
    schema = postgres_connection.schema_for_env()
    if event:
        logging.info(f'Received {len(event["Records"])} records event {event}')
        ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key_secret')
        ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

        base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'

        batch_item_failures = []
        sqs_batch_response = {}

        ordered_records = sorted(event['Records'], key=lambda r: json.loads(r['body'])['study_id'])

        for record in ordered_records:
            try:
                request_body = json.loads(record['body'])

                logging.info(f'Processing record {request_body}')

                request_id = request_body['request_id']
                study_id = request_body['study_id']

                response = http.request('GET', f'{base_url}&id={study_id}')

                summary = json.loads(response.data)['result'][f'{study_id}']
                _summary_process(schema, request_id, int(study_id), summary, output_sqs)

            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred: {str(exception)}')
        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def _summary_process(schema: str, request_id: str, study_id: int, summary: str, output_sqs: str):
    try:
        logging.debug(f'Study summary from study {study_id} is {summary}')
        geo_entity = _extract_geo_entity_from_summaries(summary)

        if geo_entity is not None and _is_study_pending_to_be_processed(schema, request_id, study_id, geo_entity):
            logging.info(f'Retrieved geo {geo_entity.identifier} for study {study_id}')
            _store_geo_entity_in_db(schema, request_id, study_id, geo_entity)

            if geo_entity.geo_entity_type is GeoEntityType.GSE:
                message = {'request_id': request_id, 'study_id': study_id, 'gse': geo_entity.identifier}
                sqs.send_message(QueueUrl=output_sqs, MessageBody=json.dumps(message))
                logging.info(f'Sent message {message} for study {study_id}')
        else:
            logging.info(f'The record with request_id {request_id} and study_id {study_id} has already been processed')
    except Exception as exception:
        if exception is not SystemError:
            logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _extract_geo_entity_from_summaries(summary: str) -> GeoEntity:
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


def _store_geo_entity_in_db(schema: str, request_id: str, study_id: int, geo_entity: GeoEntity):
    try:
        statement = f"""insert into {schema}.{geo_entity.geo_entity_type.value['table']}
                        (ncbi_id, request_id, {geo_entity.geo_entity_type.value['short_name']})
                        values (%s, %s, %s);"""
        parameters = (study_id, request_id, geo_entity.identifier)
        postgres_connection.execute_write_statement(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception


def _is_study_pending_to_be_processed(schema: str, request_id: str, study_id: int, geo_entity: GeoEntity) -> bool:
    try:
        statement = f"""select id from {schema}.{geo_entity.geo_entity_type.value['table']}
                        where request_id=%s and ncbi_id=%s and {geo_entity.geo_entity_type.value['short_name']}=%s;"""
        parameters = (request_id, study_id, geo_entity.identifier)
        return not postgres_connection.is_row_present(statement, parameters)
    except Exception as exception:
        logging.error(f'An exception has occurred: {str(exception)}')
        raise exception
