resource "aws_cloudwatch_log_group" "sra_collector_logs" {
  name              = "/aws/api_gateway/${aws_apigatewayv2_api.sra_collector_api.name}"
  retention_in_days = 30
}

resource "aws_cloudwatch_metric_alarm" "study_ids_dlq_overfill_alarm" {
  alarm_name          = "study_ids_dlq_overfill"
  evaluation_periods  = 1
  period              = 300
  namespace           = "AWS/SQS"
  dimensions          = { QueueName = aws_sqs_queue.study_ids_dlq.name }
  metric_name         = "ApproximateNumberOfMessagesVisible"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  statistic           = "Sum"
  treat_missing_data  = "ignore"
}

resource "aws_cloudwatch_metric_alarm" "pending_srp_dlq-overfill-alarm" {
  alarm_name          = "pending_srp_dlq_overfill"
  evaluation_periods  = 1
  period              = 300
  namespace           = "AWS/SQS"
  dimensions          = { QueueName = aws_sqs_queue.pending_srp_dlq.name }
  metric_name         = "ApproximateNumberOfMessagesVisible"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  statistic           = "Sum"
  treat_missing_data  = "ignore"
} //TODO missing actions on alarm for every CW alarm

resource "aws_cloudwatch_metric_alarm" "study_summaries_dlq_overfill_alarm" {
  alarm_name          = "study_summaries_dlq_overfill"
  evaluation_periods  = 1
  period              = 300
  namespace           = "AWS/SQS"
  dimensions          = { QueueName = aws_sqs_queue.study_ids_dlq.name }
  metric_name         = "ApproximateNumberOfMessagesVisible"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  statistic           = "Sum"
  treat_missing_data  = "ignore"
}
