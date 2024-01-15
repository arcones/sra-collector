output "get_study_srp_function_name" {
  value = aws_lambda_function.function.function_name
}

output "cloudwatch_log_group_arn" {
  value = module.cloudwatch.cloudwatch_log_group_arn
}
