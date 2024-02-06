import logging
import os

sqs_prefix = 'https://sqs.eu-central-1.amazonaws.com/120715685161/'


def params_per_env(lambda_name: str) -> [str, str]:
    sqs_name = 'integration_test_queue'
    db_schema = 'sracollector_dev'
    if os.environ['ENV'] == 'prod':
        db_schema = 'sracollector'
        if lambda_name == 'A_get_user_query':
            sqs_name = 'A_user_query'
        elif lambda_name == 'B_get_query_pages':
            sqs_name = 'B_query_pages'
        elif lambda_name == 'C_get_study_ids':
            sqs_name = 'C_study_ids'
        elif lambda_name == 'D_get_study_gse':
            sqs_name = 'D_gses'
        elif lambda_name == 'E1_get_study_srp':
            sqs_name = 'E1_srps'
        elif lambda_name == 'F_get_study_srrs':
            sqs_name = 'F_srrs'

    output_sqs = sqs_prefix + sqs_name

    print(f'Queue in use is {output_sqs}')
    print(f'DB schema in use is {db_schema}')

    return output_sqs, db_schema
