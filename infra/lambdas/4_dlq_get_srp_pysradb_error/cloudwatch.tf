resource "aws_cloudwatch_log_group" "dlq_get_srp_pysradb_error" {
  name              = "/aws/lambda/${aws_lambda_function.dlq_get_srp_pysradb_error.function_name}"
  retention_in_days = 7
  tags              = var.tags
}
