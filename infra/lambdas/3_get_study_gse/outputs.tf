output "get_study_gse_function_name" {
  value = aws_lambda_function.get_study_gse.function_name
}

output "cloudwatch_log_group_arn" {
  value = aws_cloudwatch_log_group.lambda_logs.arn
}
