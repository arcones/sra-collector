import argparse
import json
import logging

import boto3

logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('download_all_messages_from_queue')
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser('Saves all messages from an AWS SQS queue into a file')
parser.add_argument('-q', '--queue', dest='queue', type=str, required=True, help='The name of the AWS SQS queue to save.')
parser.add_argument('-f', '--file', dest='file', type=str, required=True, help='The name of file where to save the messages')

args = parser.parse_args()

sqs = boto3.client('sqs', region_name='eu-central-1')

queue_url = sqs.get_queue_url(QueueName=args.queue)['QueueUrl']

print('Queue to download {}'.format(queue_url))

count = 0
messages = []

while True:
    response = sqs.receive_message(MaxNumberOfMessages=1, QueueUrl=queue_url, VisibilityTimeout=300)
    if 'Messages' not in response:
        break
    messages += response['Messages']

with open(args.file, 'w') as filehandle:
    for message in messages:
        filehandle.write(f'{json.dumps(message)}' + '\n')
