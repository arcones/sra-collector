output "get_user_query_invoke_arn" {
  value = module.get_user_query.get_user_query_invoke_arn
}

output "get_user_query_function_name" {
  value = module.get_user_query.get_user_query_function_name
}

output "get_user_query_log_group_arn" {
  value = module.get_user_query.cloudwatch_log_group_arn
}

output "paginate_user_query_function_name" {
  value = module.paginate_user_query.paginate_user_query_function_name
}

output "paginate_user_query_log_group_arn" {
  value = module.paginate_user_query.cloudwatch_log_group_arn
}

output "get_study_ids_function_name" {
  value = module.get_study_ids.get_study_ids_function_name
}

output "get_study_ids_log_group_arn" {
  value = module.get_study_ids.cloudwatch_log_group_arn
}

output "get_study_gse_function_name" {
  value = module.get_study_gse.get_study_gse_function_name
}

output "get_study_gse_log_group_arn" {
  value = module.get_study_gse.cloudwatch_log_group_arn
}

output "dlq_get_srp_pysradb_error_function_name" {
  value = module.dlq_get_srp_pysradb_error.dlq_get_srp_pysradb_error_function_name
}

output "dlq_get_srp_pysradb_error_log_group_arn" {
  value = module.dlq_get_srp_pysradb_error.cloudwatch_log_group_arn
}

output "get_study_srp_function_name" {
  value = module.get_study_srp.get_study_srp_function_name
}

output "get_study_srp_log_group_arn" {
  value = module.get_study_srp.cloudwatch_log_group_arn
}

output "get_study_srrs_function_name" {
  value = module.get_study_srrs.get_study_srrs_function_name
}

output "get_study_srrs_log_group_arn" {
  value = module.get_study_srrs.cloudwatch_log_group_arn
}
