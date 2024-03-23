import json
import logging
import os
import time


# TODO hace falta boto en las deps?

class SQSHelper:
    sqs_prefix = 'https://sqs.eu-central-1.amazonaws.com/120715685161'

    def __init__(self, function_name: str, sqs):
        self.sqs = sqs

        if os.environ['ENV'] == 'prod':
            if function_name == 'A_get_user_query':
                self.output_sqs = f'{self.sqs_prefix}/A_user_query'
            elif function_name == 'B_get_query_pages':
                self.output_sqs = f'{self.sqs_prefix}/B_query_pages'
            elif function_name == 'C_get_study_ids':
                self.output_sqs = f'{self.sqs_prefix}/C_study_ids'
            elif function_name == 'D_get_study_geo':
                self.output_sqs = f'{self.sqs_prefix}/D_geos'
            elif function_name == 'E_get_study_srp':
                self.output_sqs = f'{self.sqs_prefix}/E_srps'
            elif function_name == 'F_get_study_srrs':
                self.output_sqs = f'{self.sqs_prefix}/F_srrs'
            elif function_name == 'G_get_srr_metadata':
                self.output_sqs = f'{self.sqs_prefix}/G_srr_metadata'
        else:
            self.output_sqs = f'{self.sqs_prefix}/integration_test_queue'

    def send(self, message_body: dict = None, message_bodies: [dict] = None):
        if message_body is not None and message_bodies is not None:
            raise ValueError('Either message_body or message_bodies should be provided, not both')

        if message_body:
            self._single_send(message_body)
        elif message_bodies:
            self._batch_send(message_bodies)

    def _single_send(self, message_body: dict):
        self.sqs.send_message(QueueUrl=self.output_sqs, MessageBody=json.dumps(message_body))
        logging.info(f'Sent {message_body} message to {self.output_sqs}')

    def _batch_send(self, message_bodies: [dict]):
        messages = []

        for message_body in message_bodies:
            messages.append({
                'Id': str(time.time()).replace('.', ''),
                'MessageBody': json.dumps(message_body)
            })

        message_batches = [messages[index:index + 10] for index in range(0, len(messages), 10)]

        for message_batch in message_batches:
            self.sqs.send_message_batch(QueueUrl=self.output_sqs, Entries=json.dumps(message_batch))

        logging.info(f'Sent {len(message_bodies)} messages to {self.output_sqs.split("/")[-1]}')
