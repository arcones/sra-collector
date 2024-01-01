resource "aws_cloudwatch_log_group" "sra_collector_logs" {
  name              = "/aws/api_gateway/${aws_apigatewayv2_api.sra_collector_api.name}"
  retention_in_days = 7
  tags              = var.tags
}

locals {
  lambdas = [
    module.lambdas.get_user_query_function_name,
    module.lambdas.paginate_user_query_function_name,
    module.lambdas.get_study_ids_function_name,
    module.lambdas.get_study_gse_function_name,
    module.lambdas.dlq_get_srp_pysradb_error_function_name,
    module.lambdas.get_study_srp_function_name,
    module.lambdas.get_study_srrs_function_name
  ]
  dlqs = [
    aws_sqs_queue.user_query_dlq.name,
    aws_sqs_queue.user_query_pages_dlq.name,
    aws_sqs_queue.study_ids_dlq.name,
    aws_sqs_queue.gses_dlq.name,
    aws_sqs_queue.srps_dlq.name,
    aws_sqs_queue.srrs_dlq.name
  ]
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  for_each            = toset(local.lambdas)
  alarm_name          = "${each.key}_lambda_error_rate"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  alarm_description   = "Lambda ${each.key} error rate exceeded 5%"
  alarm_actions       = [aws_sns_topic.admin.arn]
  ok_actions          = [aws_sns_topic.admin.arn]
  threshold           = 5

  metric_query {
    id = "errorCount"

    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 900
      stat        = "Sum"

      dimensions = {
        FunctionName = each.key
      }
    }
  }

  metric_query {
    id = "invocations"

    metric {
      metric_name = "Invocations"
      namespace   = "AWS/Lambda"
      period      = 900
      stat        = "Sum"

      dimensions = {
        FunctionName = each.key
      }
    }
  }

  metric_query {
    id = "errorRate"

    expression  = " ( errorCount / invocations ) * 100"
    label       = "Lambda error rate percentage"
    return_data = "true"
  }
}

resource "aws_cloudwatch_metric_alarm" "overfill_dlq" {
  for_each            = toset(local.dlqs)
  alarm_name          = "${each.key}_overfill_dlq"
  evaluation_periods  = 1
  period              = 300
  namespace           = "AWS/SQS"
  dimensions          = { QueueName = each.key }
  metric_name         = "ApproximateNumberOfMessagesVisible"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  statistic           = "Sum"
  treat_missing_data  = "ignore"
  alarm_actions       = [aws_sns_topic.admin.arn]
  ok_actions          = [aws_sns_topic.admin.arn]
}
