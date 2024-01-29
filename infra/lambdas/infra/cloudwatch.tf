resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.function.function_name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_subscription_filter" "subscription_filter" {
  name            = "cwl_${aws_lambda_function.function.function_name}"
  log_group_name  = aws_cloudwatch_log_group.lambda_logs.name
  destination_arn = var.cloudwatch_to_opensearch_function_arn
  filter_pattern  = ""
}
