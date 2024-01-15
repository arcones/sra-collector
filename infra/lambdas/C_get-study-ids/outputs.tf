output "get_study_ids_function_name" {
  value = module.lambda.function.function_name
}

output "cloudwatch_log_group_arn" {
  value = module.cloudwatch.cloudwatch_log_group_arn
}
