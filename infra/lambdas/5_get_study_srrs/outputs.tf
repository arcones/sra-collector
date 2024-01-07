output "get_study_srrs_function_name" {
  value = aws_lambda_function.get_study_srrs.function_name
}

output "cloudwatch_log_group_arn" {
  value = aws_cloudwatch_log_group.lambda_logs.arn
}
