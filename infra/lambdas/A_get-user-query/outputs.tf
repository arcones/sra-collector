output "get_user_query_invoke_arn" {
  value = aws_lambda_function.function.invoke_arn
}

output "get_user_query_function_name" {
  value = aws_lambda_function.function.function_name
}

output "cloudwatch_log_group_arn" {
  value = module.cloudwatch.cloudwatch_log_group_arn
}
