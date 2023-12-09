import json
import logging

import boto3
from pysradb import SRAweb

sqs = boto3.client('sqs', region_name='eu-central-1')

logging.basicConfig(format='%(levelname)s %(message)s')
logger = logging.getLogger('user_query')
logger.setLevel(logging.DEBUG)

OUTPUT_SQS = 'https://sqs.eu-central-1.amazonaws.com/120715685161/study_summaries_queue'


def handler(event, context):
    if event:
        logger.debug(f'Received event {event}')
        for record in event['Records']:
            study_with_missing_srp = json.loads(record['body'])
            logger.debug(f'Received event {study_with_missing_srp}')

            gse = study_with_missing_srp['gse']
            srp = SRAweb().gse_to_srp(gse)['study_accession'][0]  ## TODO manage two SRPs scenario
            logging.debug(f'For {gse} the SRP is {srp}')

            if srp:
                logger.info(f"SRP retrieved via pysradb for {study_with_missing_srp['study_id']}, pushing message to study summaries queue")
                response = json.dumps({**study_with_missing_srp, 'srps': [srp]})
                sqs.send_message(QueueUrl=OUTPUT_SQS, MessageBody=response)
                logger.debug(f'Sent event to {OUTPUT_SQS} with body {response}')
