import json
import logging

from pysradb import SRAweb


def handler(event, context):
    try:
        if event:
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
    except Exception as e:
        logging.exception(f'An exception has occurred: {e}')
