import json
import logging

import boto3
import urllib3

logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('user_query')
logger.setLevel(logging.DEBUG) ## TODO reduce log level

NCBI_RETRY_MAX = 50

secrets = boto3.client('secretsmanager', region_name='eu-central-1')
sqs = boto3.client('sqs', region_name='eu-central-1')

http = urllib3.PoolManager()


def handler(event, context):
    if event:
        ncbi_api_key_secret = secrets.get_secret_value(SecretId='ncbi_api_key')
        ncbi_api_key = json.loads(ncbi_api_key_secret['SecretString'])['value']

        base_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&retmode=json&api_key={ncbi_api_key}'

        for record in event['Records']:
            logger.debug(f'Record received {record}')
            study_request = json.loads(record['body'])
            study_id = study_request['study_id']

            url = f'{base_url}&id={study_id}'
            retries_count = 1
            while retries_count < NCBI_RETRY_MAX:
                response = http.request('GET', url)
                if response.status == 200:
                    summary = json.loads(response.data)['result'][study_id]
                    _summary_process(study_request, summary, record['attributes']['MessageGroupId'])
                else:
                    logger.info(f'HTTP GET finished with unexpected code {response.status} in retry #{retries_count} ==> {url}')
                    retries_count += 1
                    logger.info(f'Retries incremented to {retries_count}')
            raise Exception(f'Unable to fetch {study_id} in {NCBI_RETRY_MAX} attempts')


def _summary_process(study_request, summary, message_group_id):
    logger.debug(f"Study summary from study {study_request['study_id']} is {summary}")
    gse = _extract_gse_from_summaries(summary)
    srps = _extract_srp_from_summaries(summary)

    if len(srps) > 0:
        logger.debug(f"SRPs retrieved for {study_request['study_id']}, sending message to study summaries queue")
        message = {**study_request, 'gse': gse, 'srps': srps}
        return sqs.send_message(
            QueueUrl='https://sqs.eu-central-1.amazonaws.com/120715685161/study_summaries_queue.fifo',
            MessageBody=json.dumps(message),
            MessageGroupId=message_group_id
        )
    else:
        logger.debug(f"None SRPs retrieved for {study_request['study_id']}, sending message to pending SRPs queue")
        message = {**study_request, 'gse': gse}
        return sqs.send_message(
            QueueUrl='https://sqs.eu-central-1.amazonaws.com/120715685161/pending_srp_queue.fifo',
            MessageBody=json.dumps(message),
            MessageGroupId=message_group_id
        )


def _extract_gse_from_summaries(summary) -> str:
    if summary['entrytype'] == 'GSE':
        return summary['accession']
    else:
        logger.error(f'For summary {summary} there are none GSE entrytype')


def _extract_srp_from_summaries(summary) -> list[str]:
    logger.debug(f'Extracting SRPs from {summary}')
    srps = []
    if summary['extrelations']:
        for extrelation in summary['extrelations']:
            sra_targetobject = extrelation['targetobject']
            if sra_targetobject.startswith('SRP'):
                srps.append(sra_targetobject)
    return srps
