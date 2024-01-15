output "dlq_get_srp_pysradb_error_function_name" {
  value = aws_lambda_function.function.function_name
}

output "cloudwatch_log_group_arn" {
  value = aws_cloudwatch_log_group.lambda_logs.arn
}
