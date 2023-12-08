import json
import logging

from pysradb import SRAweb

logging.basicConfig(format='%(levelname)s %(message)s')
logger = logging.getLogger('user_query')
logger.setLevel(logging.INFO)


def handler(event, context):
    test = SRAweb()
    logger.info(f'For GSE189432, the SRP is {test.gse_to_srp("GSE189432")}')
    # if event:
    #     for record in event['Records']:
    #         missing_srp = json.loads(record['body'])
    #         logger.info(f'Received event {missing_srp}')
