import json
import logging

from pysradb import SRAweb
# from lambda_log_support import lambda_log_support


def handler(event, context):
    try:
        if event:
            request_id = json.loads(event['Records'][0]['body'])['request_id']
            # lambda_log_support.configure_logger(request_id, context.aws_request_id)
            logging.info(f'Received event {event}')
            for record in event['Records']:
                study_with_missing_srp = json.loads(record['body'])
                logging.info(f'Received event {study_with_missing_srp}')

                study_id = study_with_missing_srp['study_id']
                gse = study_with_missing_srp['gse']

                try:
                    srp = SRAweb().gse_to_srp(gse)['study_accession'][0]
                    logging.error(f'For study {study_id} with {gse} the SRP is {srp}, so it was possible to extract it. Investigate how this ended in DLQ')
                except AttributeError as attribute_error:
                    logging.error(f'For study {study_id} with {gse}, pysradb produced attribute error with name {attribute_error.name}')
                except ValueError as value_error:
                    if value_error.args[0] == 'All arrays must be of the same length':
                        logging.error(f'For study {study_id} with {gse}, pysradb produced value error with {value_error.args[0]}')
                    else:
                        logging.error(f'For study {study_id} with {gse}, pysradb produced value error with {value_error.args[0]}')
    except:
        logging.exception(f'An exception has occurred')
