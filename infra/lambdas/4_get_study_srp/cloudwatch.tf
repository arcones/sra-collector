resource "aws_cloudwatch_log_group" "get_study_srp" {
  name              = "/aws/lambda/${aws_lambda_function.get_study_srp.function_name}"
  retention_in_days = 7
  tags              = var.tags
}
