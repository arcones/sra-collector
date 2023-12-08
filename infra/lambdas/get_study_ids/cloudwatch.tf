resource "aws_cloudwatch_log_group" "get_study_ids_logs" {
  name              = "/aws/lambda/${aws_lambda_function.get_study_ids.function_name}"
  retention_in_days = 30
}
