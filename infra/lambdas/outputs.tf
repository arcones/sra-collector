output "get_user_query_invoke_arn" {
  value = module.A_get_user_query_lambda.function.invoke_arn
}

output "get_user_query_function_name" {
  value = module.A_get_user_query_lambda.function.function_name
}

output "get_user_query_log_group_arn" {
  value = module.A_get_user_query_lambda.cloudwatch_log_group_arn
}

output "get_query_pages_function_name" {
  value = module.B_get_query_pages_lambda.function.function_name
}

output "get_query_pages_log_group_arn" {
  value = module.B_get_query_pages_lambda.cloudwatch_log_group_arn
}

output "get_study_ids_function_name" {
  value = module.C_get_study_ids_lambda.function.function_name
}

output "get_study_ids_log_group_arn" {
  value = module.C_get_study_ids_lambda.cloudwatch_log_group_arn
}

output "get_study_gse_function_name" {
  value = module.D_get_study_gse_lambda.function.function_name
}

output "get_study_gse_log_group_arn" {
  value = module.D_get_study_gse_lambda.cloudwatch_log_group_arn
}

output "dlq_get_srp_pysradb_error_function_name" {
  value = module.E2_dlq_get_srp_pysradb_error_lambda.function.function_name
}

output "dlq_get_srp_pysradb_error_log_group_arn" {
  value = module.E2_dlq_get_srp_pysradb_error_lambda.cloudwatch_log_group_arn
}

output "get_study_srp_function_name" {
  value = module.E_get_study_srp_lambda.function.function_name
}

output "get_study_srp_log_group_arn" {
  value = module.E_get_study_srp_lambda.cloudwatch_log_group_arn
}

output "get_study_srrs_function_name" {
  value = module.F_get_study_srrs_lambda.function.function_name
}

output "get_study_srrs_log_group_arn" {
  value = module.F_get_study_srrs_lambda.cloudwatch_log_group_arn
}
