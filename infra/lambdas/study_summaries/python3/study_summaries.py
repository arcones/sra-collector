import json
import logging

import boto3

secrets = boto3.client('secretsmanager', region_name='eu-central-1')


def handler(event, context):
    if event:
        batch_item_failures = []
        sqs_batch_response = {}

        for record in event['Records']:
            try:
                print(f'La record es {record}')
            except Exception as e:
                batch_item_failures.append({'itemIdentifier': record['messageId']})

        sqs_batch_response['batchItemFailures'] = batch_item_failures
        print(f'La sqs batch response es {sqs_batch_response}')

        secret = secrets.get_secret_value(SecretId='ncbi_api_key')

        print(f'El secreto es {secret}')
        print(f'Intento de parseo sin coger el valor {json.loads(secret)}')
        print(f"Intento de parseo cogiendo el valor {json.loads(secret)['value']}")

        return sqs_batch_response
    #
    #
    # async def esummary_study(self, study_id: int) -> str:
    #     logging.debug(f'Started get summary for study ==> {study_id}')
    #     retries_count = 1
    #     while retries_count < self.NCBI_RETRY_MAX:
    #         url = self._get_authenticated_url(study_id)
    #         async with aiohttp.ClientSession() as session:
    #             logging.debug(f'HTTP GET started ==> {url}')
    #             async with session.get(url) as response:
    #                 logging.debug(f'HTTP GET Done ==> {url}')
    #                 if response.status == 200:
    #                     logging.debug(f'HTTP GET finished with expected code {response.status} in retry #{retries_count} ==> {url}')
    #                     return json.loads(await response.text())
    #                 else:
    #                     logging.debug(f'HTTP GET finished with unexpected code {response.status} in retry #{retries_count} ==> {url}')
    #                     retries_count += 1
    #                     logging.debug(f'Retries incremented to {retries_count}')
    #     raise Exception(f'Unable to fetch {study_id} in {self.NCBI_RETRY_MAX} attempts')
    #
    # def _get_authenticated_url(self, study_id):
    #     api_key = random.choice(self.NCBI_API_KEYS)
    #     return f'{self.NCBI_ESUMMARY_GDS_URL}&id={study_id}' + f'&api_key={api_key}'
