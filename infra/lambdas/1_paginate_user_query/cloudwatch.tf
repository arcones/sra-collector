resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_subscription_filter" "get_user_query_logs_subscription_filter" {
  name            = "cwl-${basename(aws_cloudwatch_log_group.lambda_logs.name)}"
  log_group_name  = aws_cloudwatch_log_group.lambda_logs.name
  destination_arn = var.cloudwatch_to_opensearch_function_arn
  filter_pattern  = "%\\[INFO\\]|\\[DEBUG\\]|\\[ERROR\\]%"
}
