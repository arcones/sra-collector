resource "aws_cloudwatch_log_group" "get_study_gse_logs" {
  name              = "/aws/lambda/${aws_lambda_function.get_study_gse.function_name}"
  retention_in_days = 7
  tags              = var.tags
}
