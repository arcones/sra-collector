import json
import logging

import boto3
import psycopg2


logging.basicConfig(level=logging.INFO)
secrets = boto3.client('secretsmanager', region_name='eu-central-1')

def get_connection():
    database_credentials = secrets.get_secret_value(SecretId='rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6')
    username = json.loads(database_credentials['SecretString'])['username']
    password = json.loads(database_credentials['SecretString'])['password']
    host = 'sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com'

    connection_string = f"host={host} dbname='sracollector' user='{username}' password='{password}'"
    return psycopg2.connect(connection_string)
