resource "aws_cloudwatch_log_group" "sra_collector_logs" {
  name              = "/aws/api_gateway/${aws_apigatewayv2_api.sra_collector_api.name}"
  retention_in_days = 7
  tags              = var.tags
}


resource "aws_iam_role_policy_attachment" "lambda_basic_policy" {
  role       = aws_iam_role.cw_2_os_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role" "cw_2_os_role" {
  name = "cw_2_os_role"
  assume_role_policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action = ["sts:AssumeRole", ],
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "cw_2_os_policy" {
  name = "cw_2_os_policy"
  role = aws_iam_role.cw_2_os_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["es:*", ],
        Effect   = "Allow",
        Resource = "arn:aws:es:${var.aws_region}:${var.aws_account_id}:domain/${local.domain_name}/*"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "get_user_query_logs" {
  name              = "/aws/lambda/${aws_lambda_function.cw_2_os.function_name}"
  retention_in_days = 7
}


resource "aws_lambda_function" "cw_2_os" {
  function_name = "cw_2_os_lambda"
  role          = aws_iam_role.cw_2_os_role.arn
  handler       = "cw_2_os.handler"
  runtime       = "nodejs18.x"
  s3_bucket     = aws_s3_bucket.lambdas.id
  s3_key        = "cw_2_os.zip"
  timeout       = 300
  lifecycle {
    replace_triggered_by = [null_resource.code_watcher]
  }
  tags = var.tags
}

resource "null_resource" "code_watcher" {
  triggers = {
    dir_sha1 = sha1(join("", [for file in fileset("cw_2_os_code", "*") : filesha1("cw_2_os_code/${file}")]))
  }
}



resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCWLogs"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cw_2_os.function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "${aws_cloudwatch_log_group.sra_collector_logs.arn}:*"
}

data "archive_file" "cw_2_os_code" {
  type        = "zip"
  source_file = "cw_2_os_code/cw_2_os.js"
  output_path = "cw_2_os.zip"
}

resource "aws_s3_object" "cw_2_os_s3_object" {
  bucket = aws_s3_bucket.lambdas.id
  key    = "cw_2_os.zip"
  source = data.archive_file.cw_2_os_code.output_path
  etag   = filemd5(data.archive_file.cw_2_os_code.output_path)
  tags   = var.tags
}


resource "aws_cloudwatch_log_subscription_filter" "sra_collector_logs_subscription_filter" {
  name            = "cwl-${basename(aws_cloudwatch_log_group.sra_collector_logs.name)}"
  log_group_name  = aws_cloudwatch_log_group.sra_collector_logs.name
  destination_arn = aws_lambda_function.cw_2_os.arn
  filter_pattern  = ""
}

locals {
  lambdas_2_max_error_ratio_expected = {
    "${module.lambdas.get_user_query_function_name}"            = 1,
    "${module.lambdas.paginate_user_query_function_name}"       = 5,
    "${module.lambdas.get_study_ids_function_name}"             = 5,
    "${module.lambdas.get_study_gse_function_name}"             = 5,
    "${module.lambdas.dlq_get_srp_pysradb_error_function_name}" = 5,
    "${module.lambdas.get_study_srp_function_name}"             = 10,
    "${module.lambdas.get_study_srrs_function_name}"            = 10
  }
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
  tags = var.tags
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
  tags = var.tags
}
