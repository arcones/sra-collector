resource "aws_cloudwatch_log_group" "cloudwatch_to_opensearch_logs" {
  name              = "/aws/lambda/${aws_lambda_function.cloudwatch_to_opensearch.function_name}"
  retention_in_days = 7
}
