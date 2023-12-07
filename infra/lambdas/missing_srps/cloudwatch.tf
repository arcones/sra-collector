resource "aws_cloudwatch_log_group" "missing_srps_logs" {
  name              = "/aws/lambda/${aws_lambda_function.missing_srps.function_name}"
  retention_in_days = 30
}
