resource "aws_cloudwatch_log_group" "get_study_srrs" {
  name              = "/aws/lambda/${aws_lambda_function.get_study_srrs.function_name}"
  retention_in_days = 7
}
