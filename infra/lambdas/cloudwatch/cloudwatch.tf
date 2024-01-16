resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_cloudwatch_log_subscription_filter" "subscription_filter" {
  name            = "cwl_${var.function_name}"
  log_group_name  = aws_cloudwatch_log_group.lambda_logs.name
  destination_arn = var.cloudwatch_to_opensearch_function_arn
  filter_pattern  = "%INFO%"
}

//TODO pasar esto tb al lambda module -> renombrar carpeta contenedora... lambda lambdas no son nombres muy originales
