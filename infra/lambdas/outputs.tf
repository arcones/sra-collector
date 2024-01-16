output "get_user_query_invoke_arn" {
  value = module.A_get-user-query-lambda.function.invoke_arn
}

output "get_user_query_function_name" {
  value = module.A_get-user-query-lambda.function.function_name
}

output "get_user_query_log_group_arn" {
  value = module.A_get-user-query-cloudwatch.cloudwatch_log_group_arn
}

output "paginate_user_query_function_name" {
  value = module.B_paginate_user_query-lambda.function.function_name
}

output "paginate_user_query_log_group_arn" {
  value = module.B_paginate_user_query-cloudwatch.cloudwatch_log_group_arn
}

output "get_study_ids_function_name" {
  value = module.C_get-study-ids-lambda.function.function_name
}

output "get_study_ids_log_group_arn" {
  value = module.C_get-study-ids-cloudwatch.cloudwatch_log_group_arn
}

output "get_study_gse_function_name" {
  value = module.D_get-study-gse-lambda.function.function_name
}

output "get_study_gse_log_group_arn" {
  value = module.D_get-study-gse-cloudwatch.cloudwatch_log_group_arn
}

output "dlq_get_srp_pysradb_error_function_name" {
  value = module.E2_dlq-get-srp-pysradb-error-lambda.function.function_name
}

output "dlq_get_srp_pysradb_error_log_group_arn" {
  value = module.E2_dlq-get-srp-pysradb-error-cloudwatch.cloudwatch_log_group_arn
}

output "get_study_srp_function_name" {
  value = module.E1_get-study-srp-lambda.function.function_name
}

output "get_study_srp_log_group_arn" {
  value = module.E1_get-study-srp-cloudwatch.cloudwatch_log_group_arn
}

output "get_study_srrs_function_name" {
  value = module.F_get-study-srrs-lambda.function.function_name
}

output "get_study_srrs_log_group_arn" {
  value = module.F_get-study-srrs-cloudwatch.cloudwatch_log_group_arn
}
