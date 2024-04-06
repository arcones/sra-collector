import logging
import os


class S3Helper:

    def __init__(self, s3):
        self.s3 = s3
        if os.environ['ENV'] == 'prod':
            self.bucket_name = 'sra-collector-reports'
        else:
            self.bucket_name = 'integration-tests-s3'

    def upload_file(self, path: str, filename: str):
        try:
            self.s3.upload_file(path, self.bucket_name, filename)
        except Exception as exception:
            logging.error(f'An exception has occurred in {self.upload_file.__name__}: {str(exception)}')
            raise exception

    def download_file(self, key: str):
        try:
            self.s3.download_file(self.bucket_name, key, f'/tmp/{key}')
        except Exception as exception:
            logging.error(f'An exception has occurred in {self.download_file.__name__}: {str(exception)}')
            raise exception
