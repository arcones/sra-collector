resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${basename(path.module)}"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_cloudwatch_log_subscription_filter" "subscription_filter" {
  name            = "cwl_${basename(path.module)}"
  log_group_name  = aws_cloudwatch_log_group.lambda_logs.name
  destination_arn = var.cloudwatch_to_opensearch_function_arn
  filter_pattern  = "%INFO%"
}
