import csv
import json
import logging
import os

import boto3
from db_connection.db_connection import DBConnectionManager
from s3_helper.s3_helper import S3Helper

s3 = boto3.client('s3', region_name='eu-central-1')


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

                    request_id = request_body['request_id']

                    request_status = get_request_status(database_holder, request_id)

                    if request_status == 'PENDING':
                        report = generate_report(database_holder, request_id)
                        filename = f'Report_{request_id}.csv'
                        path = os.path.join('/tmp', filename)
                        with open(path, 'w', newline='') as csvfile:
                            csv_writer = csv.writer(csvfile)
                            csv_writer.writerow(['REQUEST_ID', 'QUERY', 'NCBI_STUDY', 'GSE', 'SRP', 'SRR', 'SPOTS', 'BASES', 'ORGANISM',
                                                 'NSPOTS', 'LAYOUT', 'PHRED_READ_OVER_37', 'READ_0_COUNT', 'READ_0_AVERAGE',
                                                 'READ_0_STDEV', 'READ_1_COUNT', 'READ_1_AVERAGE', 'READ_1_STDEV'])
                            csv_writer.writerows(report)
                        S3Helper(s3).upload_file(path, filename)
                        update_request_status(database_holder, request_id)
                        logging.info(f'Uploaded {filename} to S3')
                    elif request_status == 'COMPLETED':
                        logging.info(f'For {request_id} the CSV was already generated')
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')

        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def get_request_status(database_holder, request_id: int) -> (str, str):
    try:
        statement = 'select status from request where id=%s'
        parameters = (request_id,)
        rows = database_holder.execute_read_statement(statement, parameters)[0]
        return rows[0]
    except Exception as exception:
        logging.error(f'An exception has occurred in {get_request_status.__name__}: {str(exception)}')
        raise exception


def generate_report(database_holder, request_id: str) -> [[]]:
    try:
        statement = ('SELECT R.ID, R.QUERY, NS.NCBI_ID, GS.GSE, SP.SRP, SR.SRR, SRM.SPOTS AS TOTAL_SPOTS, '
                     'SRM.BASES AS TOTAL_BASES, SRM.ORGANISM, SRMSR.NSPOTS, SRMSR.LAYOUT, '
                     'SUM(CASE WHEN SRMP.SCORE >= 37 THEN SRMP.READ_COUNT ELSE 0 END) / SRM.BASES AS PHRED_READ_COUNT_OVER_37, '
                     'SRMSR.READ_0_COUNT, SRMSR.READ_0_AVERAGE, SRMSR.READ_0_STDEV, '
                     'SRMSR.READ_1_COUNT, SRMSR.READ_1_AVERAGE, SRMSR.READ_1_STDEV '
                     'FROM SRA_RUN_METADATA SRM '
                     'JOIN SRA_RUN_METADATA_PHRED SRMP ON SRM.ID = SRMP.SRA_RUN_METADATA_ID '
                     'JOIN SRA_RUN_METADATA_STATISTIC_READ SRMSR ON SRMSR.SRA_RUN_METADATA_ID = SRM.ID '
                     'JOIN SRA_RUN SR ON SR.ID = SRM.SRA_RUN_ID '
                     'JOIN SRA_PROJECT SP ON SR.SRA_PROJECT_ID = SP.ID '
                     'JOIN GEO_STUDY GS ON SP.GEO_STUDY_ID = GS.ID '
                     'JOIN NCBI_STUDY NS ON GS.NCBI_STUDY_ID = NS.ID '
                     'JOIN REQUEST R ON NS.REQUEST_ID = R.ID '
                     'WHERE R.ID =%s '
                     'GROUP BY R.ID, R.QUERY, NS.NCBI_ID, GS.GSE, SP.SRP, SR.SRR, SRM.SPOTS, SRM.BASES, '
                     'SRM.ORGANISM, SRMSR.NSPOTS, SRMSR.LAYOUT, SRMSR.READ_0_COUNT, SRMSR.READ_0_AVERAGE, '
                     'SRMSR.READ_0_STDEV, SRMSR.READ_1_COUNT, SRMSR.READ_1_AVERAGE, SRMSR.READ_1_STDEV; ')
        return database_holder.execute_read_statement(statement, (request_id,))
    except Exception as exception:
        logging.error(f'An exception has occurred in {generate_report.__name__}: {str(exception)}')
        raise exception


def update_request_status(database_holder, request_id: str):
    try:
        statement = "UPDATE REQUEST SET STATUS='COMPLETED' WHERE ID=%s"
        database_holder.execute_write_statement(statement, (request_id,))
    except Exception as exception:
        logging.error(f'An exception has occurred in {update_request_status.__name__}: {str(exception)}')
        raise exception
