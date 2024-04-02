import json
import logging
import os
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

import boto3
from db_connection.db_connection import DBConnectionManager
from s3_helper.s3_helper import S3Helper

ses = boto3.client('ses', region_name='eu-central-1')
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

                    if 'filename' in request_body:
                        filename = request_body['filename']
                        request_id = re.search(r'Report_(.+)\.csv', filename).group(1)
                        file = S3Helper(s3).download_file(filename)
                        mail_address = get_mail_address_for_request(database_holder, request_id)
                        ses.send_raw_email(
                            Source='noreply@sracollector.com', ## TODO DRY
                            Destinations=[mail_address, 'marta.arcones@gmail.com'],
                            RawMessage={'Data': compose_mail(request_id, mail_address, f'/tmp/{filename}')}
                        )
                    elif 'reason' in request_body:
                        reason = request_body['reason']
                        ses.send_email(
                            Source='noreply@sracollector.com',
                            Destination={'ToAddresses': [mail_address], 'BccAddresses': ['marta.arcones@gmail.com']},
                            Message=reason
                        ) # TODO AQUIMEQUEDE en ppio, el codigo está terminado, falta probarlo a base de tests...
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')

        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def get_mail_address_for_request(database_holder, request_id: str) -> str:
    try:
        statement = f'select mail from request where id=%s;'
        return database_holder.execute_read_statement(statement, (request_id,))[0][0]
    except Exception as exception:
        logging.error(
            f'An exception has occurred in {get_mail_address_for_request.__name__}: {str(exception)}')  # TODO el completed en la tabla REQUEST quiza deberia ser segun el mail queda enviado? estados PENDING, EXTRACT, COMPLETED?
        raise exception


def compose_mail(request_id: str, recipient: str, attachment_path: str) -> str:
    mail = MIMEMultipart()
    mail['Subject'] = f'Results for {request_id} query to SRA-Collector'
    mail['From'] = 'noreply@sracollector.com' ## TODO DRY
    mail['To'] = recipient
    mail['Bcc'] = 'marta.arcones@gmail.com'  # TODO parametrizar envvar para webmaster ## TODO DRY also

    with open(attachment_path, 'rb') as f:
        attachment = MIMEApplication(f.read())
        attachment.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(attachment_path)}"')
        mail.attach(attachment)

    return mail.as_string()
