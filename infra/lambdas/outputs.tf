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

output "get_study_geo_function_name" {
  value = module.D_get_study_geo_lambda.function.function_name
}

output "get_study_geo_log_group_arn" {
  value = module.D_get_study_geo_lambda.cloudwatch_log_group_arn
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

output "get_srr_metadata_function_name" {
  value = module.G_get_srr_metadata_lambda.function.function_name
}

output "get_srr_metadata_log_group_arn" {
  value = module.G_get_srr_metadata_lambda.cloudwatch_log_group_arn
}

output "generate_report_function_name" {
  value = module.H_generate_report_lambda.function.function_name
}

output "generate_report_log_group_arn" {
  value = module.H_generate_report_lambda.cloudwatch_log_group_arn
}

output "send_email_function_name" {
  value = module.I_send_email_lambda.function.function_name
}

output "send_email_log_group_arn" {
  value = module.I_send_email_lambda.cloudwatch_log_group_arn
}
