output "get_user_query_invoke_arn" {
  value = module.get_user_query.get_user_query_invoke_arn
}

output "get_user_query_function_name" {
  value = module.get_user_query.get_user_query_function_name
}

output "paginate_user_query_function_name" {
  value = module.paginate_user_query.paginate_user_query_function_name
}

output "get_study_ids_function_name" {
  value = module.get_study_ids.get_study_ids_function_name
}

output "get_study_gse_function_name" {
  value = module.get_study_gse.get_study_gse_function_name
}

output "dlq_get_srp_pysradb_error_function_name" {
  value = module.dlq_get_srp_pysradb_error.dlq_get_srp_pysradb_error_function_name
}

output "get_study_srp_function_name" {
  value = module.get_study_srp.get_study_srp_function_name
}

output "get_study_srrs_function_name" {
  value = module.get_study_srrs.get_study_srrs_function_name
}
