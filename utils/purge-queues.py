import logging
import time

import boto3

logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('user_query')
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs', region_name='eu-central-1')

logger.info(f'Listing queues...')
queue_urls = sqs.list_queues()['QueueUrls']
logger.info(f'Listed {len(queue_urls)} queues')

for queue_url in queue_urls:
    try:
        logger.info(f'Purging queue {queue_url}...')
        response = sqs.purge_queue(QueueUrl=queue_url)
        logger.info(f'Purged queue {queue_url}')
    except sqs.exceptions.PurgeQueueInProgress as purgeQueueActionInProgress:
        logger.info(f'There is a purge action already in progress in {queue_url}')
