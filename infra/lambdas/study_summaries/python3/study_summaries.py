import json
import logging

import boto3
import urllib3

NCBI_RETRY_MAX = 50

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
http = urllib3.PoolManager()


def handler(event, context):
    if event:
        ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key')
        ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

        base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils&api_key={ncbi_api_key}'

        for record in event['Records']:
            study_request = json.loads(record['body'])
            logging.info(f'Study request received {study_request}')

            url = f"{base_url}&id={study_request['study_id']}"
            retries_count = 1
            while retries_count < NCBI_RETRY_MAX:
                response = http.request('GET', url)
                if response.status == 200:
                    logging.info(json.loads(response.data))
                    return
                else:
                    logging.info(f'HTTP GET finished with unexpected code {response.status} in retry #{retries_count} ==> {url}')
                    retries_count += 1
                    logging.info(f'Retries incremented to {retries_count}')
            raise Exception(f"Unable to fetch {study_request['study_id']} in {NCBI_RETRY_MAX} attempts")
