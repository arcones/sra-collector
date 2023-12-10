resource "aws_cloudwatch_log_group" "study_summaries_logs" {
  name              = "/aws/lambda/${aws_lambda_function.study_summaries.function_name}"
  retention_in_days = 30
}
