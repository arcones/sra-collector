import logging

import boto3

logging.getLogger('pysradb').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)


def configure_logger(request_id: str, invocation_id: str):
    ssm = boto3.client('ssm', region_name='eu-central-1')
    log_level = ssm.get_parameter(Name='sra_collector_log_level')['Parameter']['Value']

    if log_level == 'DEBUG':
        level = logging.DEBUG
    else:
        level = logging.INFO

    root = logging.getLogger()

    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    class HandleBytes(logging.Filter):
        def filter(self, record):
            try:
                record.msg = record.msg.decode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                pass

    class RemoveLiveBreaks(logging.Filter):
        def filter(self, record):
            record.msg = record.msg.replace('\n', '').replace('\r', '')
            return record

    class EscapeDoubleQuotes(logging.Filter):
        def filter(self, record):
            import re
            record.msg = re.sub(r'([^\\])"', '\\1\\"', record.msg)
            ## Two replacements needs to be done to escape sequences of two consecutive double quotes
            record.msg = re.sub(r'([^\\])"', '\\1\\"', record.msg)
            return record

    logging.basicConfig(
        format=f'{{"level": "%(levelname)s", '
               f'"request_id": "{request_id}", '
               f'"invocation_id": "{invocation_id}", '
               f'"message": "%(message)s"}}',
        level=level)

    root.addFilter(HandleBytes())
    root.addFilter(EscapeDoubleQuotes())
    root.addFilter(RemoveLiveBreaks())
