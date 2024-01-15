output "get_user_query_invoke_arn" {
  value = module.lambda.function.invoke_arn
}

output "get_user_query_function_name" {
  value = module.lambda.function.function_name
}

output "cloudwatch_log_group_arn" {
  value = module.cloudwatch.cloudwatch_log_group_arn
}
