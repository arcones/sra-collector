import json
import logging
import os
import time


class SQSHelper:
    sqs_prefix = 'https://sqs.eu-central-1.amazonaws.com/120715685161'

    def __init__(self, sqs, function_name: str, output_sqs: str = None):
        self.sqs = sqs

        if os.environ['ENV'] == 'prod':
            if function_name == 'A_get_user_query':
                self.output_sqs = f'{self.sqs_prefix}/A_user_query' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
            elif function_name == 'B_get_query_pages':
                self.output_sqs = f'{self.sqs_prefix}/B_query_pages' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
            elif function_name == 'C_get_study_ids':
                self.output_sqs = f'{self.sqs_prefix}/C_study_ids' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
            elif function_name == 'D_get_study_geo':
                self.output_sqs = f'{self.sqs_prefix}/D_geos' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
            elif function_name == 'E_get_study_srp':
                self.output_sqs = f'{self.sqs_prefix}/E_srps' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
            elif function_name == 'F_get_study_srrs':
                self.output_sqs = f'{self.sqs_prefix}/F_srrs' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
            elif function_name == 'G_get_srr_metadata':
                self.output_sqs = f'{self.sqs_prefix}/G_srr_metadata' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
            elif function_name == 'H_generate_report':
                self.output_sqs = f'{self.sqs_prefix}/H_user_feedback' if output_sqs is None else f'{self.sqs_prefix}/{output_sqs}'
        else:
            self.output_sqs = f'{self.sqs_prefix}/integration_test_queue'

    def send(self, message_body: dict = None, message_bodies: [dict] = None):
        try:
            if message_body is not None and message_bodies is not None:
                raise ValueError('Either message_body or message_bodies should be provided, not both')

            if message_body:
                self._single_send(message_body)
            elif message_bodies:
                self._batch_send(message_bodies)
        except Exception as exception:
            logging.error(f'An exception has occurred in {self.send.__name__}: {str(exception)}')
            raise exception

    def _single_send(self, message_body: dict):
        try:
            self.sqs.send_message(QueueUrl=self.output_sqs, MessageBody=json.dumps(message_body))
            logging.info(f'Sent {message_body} message to {self.output_sqs}')
        except Exception as exception:
            logging.error(f'An exception has occurred in {self._single_send.__name__}: {str(exception)}')
            raise exception

    def _batch_send(self, message_bodies: [dict]):
        try:
            messages = []

            for message_body in message_bodies:
                messages.append({
                    'Id': str(time.time()).replace('.', ''),
                    'MessageBody': json.dumps(message_body)
                })

            message_batches = [messages[index:index + 10] for index in range(0, len(messages), 10)]

            for message_batch in message_batches:
                self.sqs.send_message_batch(QueueUrl=self.output_sqs, Entries=message_batch)

            logging.info(f'Sent {len(message_bodies)} messages to {self.output_sqs.split("/")[-1]}')
        except Exception as exception:
            logging.error(f'An exception has occurred in {self._batch_send.__name__}: {str(exception)}')
            raise exception
