import logging

from pysradb import SRAweb


def handler(event, _):
    if event:

        logging.info(f'Received {len(event["Records"])} records event {event}')

        batch_item_failures = []
        sqs_batch_response = {}

        for record in event['Records']:
            logging.info(f'Processing record {record}')
            srr = 'SRR13790594'
            raw_pysradb_data_frame = SRAweb().sra_metadata(srp=srr, detailed=True)
