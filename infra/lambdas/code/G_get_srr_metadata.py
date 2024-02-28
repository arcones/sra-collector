import logging


def handler(event, context):
    if event:

        logging.info(f'Received {len(event["Records"])} records event {event}')

        batch_item_failures = []
        sqs_batch_response = {}

        for record in event['Records']:
            logging.info(f'Processing record {record}')
