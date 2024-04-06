import json
import logging
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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

                    request_id = request_body['request_id']
                    recipient_mail_address = get_mail_address_for_request(database_holder, request_id)

                    if 'filename' in request_body:
                        filename = request_body['filename']
                        S3Helper(s3).download_file(request_body['filename'])
                        send_email(request_id, recipient_mail_address, attachment_path=f'/tmp/{filename}')
                    else:
                        send_email(request_id, recipient_mail_address, reason=request_body['reason'])
            except Exception as exception:
                batch_item_failures.append({'itemIdentifier': record['messageId']})
                logging.error(f'An exception has occurred in {handler.__name__}: {str(exception)}')

        sqs_batch_response['batchItemFailures'] = batch_item_failures
        return sqs_batch_response


def get_mail_address_for_request(database_holder, request_id: str) -> str:
    try:
        statement = 'select mail from request where id=%s;'
        return database_holder.execute_read_statement(statement, (request_id,))[0][0]
    except Exception as exception:
        logging.error(
            f'An exception has occurred in {get_mail_address_for_request.__name__}: {str(exception)}')  # TODO el completed en la tabla REQUEST quiza deberia ser segun el mail queda enviado? estados PENDING, EXTRACT, COMPLETED?
        raise exception


def send_email(request_id: str, recipient: str, attachment_path: str = None, reason: str = None) -> None:
    ses.send_raw_email(
        Source=os.environ.get('WEBMASTER_MAIL'),
        Destinations=[], ## TODO needed?
        RawMessage={'Data': compose_mail(request_id, recipient, attachment_path, reason) }
    )


def compose_mail(request_id: str, recipient: str, attachment_path: str = None, reason: str = None) -> str:
    if (attachment_path is None) == (reason is None):
        raise ValueError('Either attachment_path or reason should be provided, not both')

    mail = MIMEMultipart()
    mail['Subject'] = f'Results for {request_id} query to SRA-Collector'
    mail['From'] = os.environ.get('WEBMASTER_MAIL') ## TODO redundante con #58
    mail['To'] = recipient
    mail['Bcc'] = os.environ.get('WEBMASTER_MAIL')

    if attachment_path is not None:
        with open(attachment_path, 'rb') as attachment:
            attachment = MIMEApplication(attachment.read())
            attachment.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(attachment_path)}"')
            mail.attach(attachment)
    else:
        mail_body = MIMEText(reason, 'plain')
        mail.attach(mail_body)

    return mail.as_string()
