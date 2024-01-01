import logging

import boto3

logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('user_query')
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch', region_name='eu-central-1')

metric_alarms = cloudwatch.describe_alarms()['MetricAlarms']

metric_alarms_names = [metric_alarm['AlarmName'] for metric_alarm in metric_alarms]

logger.info(f'There are {len(metric_alarms_names)} alarms to restart')

for metric_alarm_name in metric_alarms_names:
    alarm_reset_result_code = cloudwatch.set_alarm_state(
        AlarmName='dlq_get_srp_pysradb_error_lambda_error_rate',
        StateValue='OK',
        StateReason='Manually restarted'
    )['ResponseMetadata']['HTTPStatusCode']
    if alarm_reset_result_code == 200:
        logger.info(f'Alarm reset for {metric_alarm_name} was successful')
    else:
        logger.error(f'Alarm reset for {metric_alarm_name} failed')
