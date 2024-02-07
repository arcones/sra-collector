resource "aws_cloudwatch_log_group" "sra_collector_logs" {
  name              = "/aws/api_gateway/${aws_apigatewayv2_api.sra_collector_api.name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_subscription_filter" "subscription_filter" {
  name            = "cwl_${aws_apigatewayv2_api.sra_collector_api.name}"
  log_group_name  = aws_cloudwatch_log_group.sra_collector_logs.name
  destination_arn = module.opensearch.cloudwatch_to_opensearch_function_arn
  filter_pattern  = ""
}

locals {
  lambdas_2_max_error_ratio_expected = {
    (module.lambdas.get_user_query_function_name)  = 1,
    (module.lambdas.get_query_pages_function_name) = 5,
    (module.lambdas.get_study_ids_function_name)   = 5,
    (module.lambdas.get_study_gse_function_name)   = 5,
    (module.lambdas.get_study_srp_function_name)   = 10,
    (module.lambdas.get_study_srrs_function_name)  = 10
  }
  dlqs = [
    aws_sqs_queue.A_DLQ_user_query_2_query_pages.name,
    aws_sqs_queue.B_DLQ_query_pages_2_study_ids.name,
    aws_sqs_queue.C_DLQ_study_ids_2_gses.name,
    aws_sqs_queue.D_DLQ_gses_2_srps.name,
    aws_sqs_queue.E_DLQ_srps_2_srrs.name,
  ]
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  for_each            = local.lambdas_2_max_error_ratio_expected
  alarm_name          = "${each.key}_lambda_error_rate"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  alarm_description   = "Lambda ${each.key} error rate exceeded ${each.value}%"
  alarm_actions       = [aws_sns_topic.admin.arn]
  ok_actions          = [aws_sns_topic.admin.arn]
  threshold           = each.value
  treat_missing_data  = "ignore"

  metric_query {
    id = "errorCount"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
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
      period      = 300
      stat        = "Sum"

      dimensions = {
        FunctionName = each.key
      }
    }
  }

  metric_query {
    id          = "errorRate"
    expression  = "( errorCount / invocations ) * 100"
    label       = "Lambda error rate percentage"
    return_data = "true"
  }
}

resource "aws_cloudwatch_metric_alarm" "dlq_alarm" {
  for_each            = toset(local.dlqs)
  alarm_name          = "${each.key}_overfill_dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 0
  alarm_actions       = [aws_sns_topic.admin.arn]
  ok_actions          = [aws_sns_topic.admin.arn]
  treat_missing_data  = "ignore"

  metric_query {
    id          = "e1"
    expression  = "RATE(visible_messages + not_visible_messages)"
    label       = "Error Rate"
    return_data = "true"
  }

  metric_query {
    id = "visible_messages"

    metric {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      period      = 300
      stat        = "Sum"
      unit        = "Count"

      dimensions = {
        QueueName = each.key
      }
    }
  }

  metric_query {
    id = "not_visible_messages"

    metric {
      metric_name = "ApproximateNumberOfMessagesNotVisible"
      namespace   = "AWS/SQS"
      period      = 300
      stat        = "Sum"
      unit        = "Count"

      dimensions = {
        QueueName = each.key
      }
    }
  }
}
