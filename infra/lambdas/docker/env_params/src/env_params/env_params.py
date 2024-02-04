import logging
import os

sqs_prefix = 'https://sqs.eu-central-1.amazonaws.com/120715685161/'


def params_per_env(lambda_name: str) -> [str, str]:
    sqs_name = 'integration_test_queue'
    db_schema = 'sracollector_dev'
    if os.environ['ENV'] == 'prod':
        db_schema = 'sracollector'
        if lambda_name == 'A_get_user_query':
            sqs_name = 'user_query_queue'
        elif lambda_name == 'B_paginate_user_query':
            sqs_name = 'user_query_pages_queue'
        elif lambda_name == 'C_get_study_ids':
            sqs_name = 'study_ids_queue'
        elif lambda_name == 'D_get_study_gse':
            sqs_name = 'gses_queue'
        elif lambda_name == 'E1_get_study_srp':
            sqs_name = 'srps_queue'
        elif lambda_name == 'F_get_study_srrs':
            sqs_name = 'srrs_queue'

    output_sqs = sqs_prefix + sqs_name

    print(f'Queue in use is {output_sqs}')
    print(f'DB schema in use is {db_schema}')

    return output_sqs, db_schema
