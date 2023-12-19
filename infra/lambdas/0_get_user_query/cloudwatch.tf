resource "aws_cloudwatch_log_group" "get_user_query_logs" {
  name              = "/aws/lambda/${aws_lambda_function.get_user_query.function_name}"
  retention_in_days = 7
}
