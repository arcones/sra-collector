import logging
import os

sqs_prefix = 'https://sqs.eu-central-1.amazonaws.com/120715685161/'
logger = logging.getLogger(__name__)

def params_per_env(lambda_name: str) -> [str, str]:
    sqs_name = 'integration_test_queue'
    db_schema = 'sracollector_dev'
    if os.environ['ENV'] == 'prod':
        db_schema = 'sracollector'
        if lambda_name == 'A_get_user_query':
            sqs_name = 'A_user_query'
            logger.info(f'Queue in use is {sqs_name}')
        elif lambda_name == 'B_get_query_pages':
            sqs_name = 'B_query_pages'
            logger.info(f'Queue in use is {sqs_name}')
        elif lambda_name == 'C_get_study_ids':
            sqs_name = 'C_study_ids'
            logger.info(f'Queue in use is {sqs_name}')
        elif lambda_name == 'D_get_study_gse':
            sqs_name = 'D_gses'
            logger.info(f'Queue in use is {sqs_name}')
        elif lambda_name == 'E_get_study_srp':
            sqs_name = 'E_srps'
            logger.info(f'Queue in use is {sqs_name}')
        elif lambda_name == 'F_get_study_srrs':
            sqs_name = 'F_srrs'
            logger.info(f'Queue in use is {sqs_name}')

    output_sqs = sqs_prefix + sqs_name

    logger.info(f'DB schema in use is {db_schema}')

    return output_sqs, db_schema
