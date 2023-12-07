import json
import logging

logging.basicConfig(format='%(levelname)s %(message)s')
logger = logging.getLogger('user_query')
logger.setLevel(logging.INFO)


def handler(event, context):
    if event:
        for record in event['Records']:
            missing_srp = json.loads(record['body'])
            logger.info(f'Received event {missing_srp}')
