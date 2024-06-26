data "aws_secretsmanager_secrets" "managed_rds_secret" {
  filter {
    name   = "owning-service"
    values = ["rds"]
  }
}

locals {
  rds_secret_arn = tolist(data.aws_secretsmanager_secrets.managed_rds_secret.arns)[0]
}

module "A_get_user_query_lambda" {
  source                = "./infra"
  code_path             = "${path.module}/code"
  common_libs_layer_arn = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name         = "A_get_user_query"
  queues = {
    input_sqs_arn   = null
    output_sqs_arns = [var.queues.A_user_query_sqs.A_user_query_sqs_arn]
    dlq_arn         = null
  }
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  aws_apigatewayv2_api_execution_arn    = var.aws_apigatewayv2_api_execution_arn
  cognito_pool_id                       = var.cognito_pool_id
  cognito_client_id                     = var.cognito_client_id
}

module "B_get_query_pages_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "B_get_query_pages"
  reserved_concurrent_executions = 50
  queues = {
    input_sqs_arn   = var.queues.A_user_query_sqs.A_user_query_sqs_arn
    output_sqs_arns = [var.queues.B_query_pages_sqs.B_query_pages_sqs_arn, var.queues.H_user_feedback.H_user_feedback_arn]
    dlq_arn         = var.queues.A_to_B_DLQ_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  webmaster_mail                        = var.webmaster_mail
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  timeout                               = var.queues.A_user_query_sqs.A_user_query_sqs_visibility_timeout / 2
}

module "C_get_study_ids_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "C_get_study_ids"
  reserved_concurrent_executions = 50
  queues = {
    input_sqs_arn   = var.queues.B_query_pages_sqs.B_query_pages_sqs_arn
    output_sqs_arns = [var.queues.C_study_ids_sqs.C_study_ids_sqs_arn]
    dlq_arn         = var.queues.B_to_C_DLQ_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  timeout                               = var.queues.B_query_pages_sqs.B_query_pages_sqs_visibility_timeout / 2
}

module "D_get_study_geo_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "D_get_study_geo"
  reserved_concurrent_executions = 50
  queues = {
    input_sqs_arn   = var.queues.C_study_ids_sqs.C_study_ids_sqs_arn
    output_sqs_arns = [var.queues.D_geos_sqs.D_geos_sqs_arn]
    dlq_arn         = var.queues.C_to_D_DLQ_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  ncbi_secret_arn                       = var.ncbi_api_key_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  timeout                               = var.queues.C_study_ids_sqs.C_study_ids_sqs_visibility_timeout / 2
  batch_size                            = 50
  batch_size_window                     = 3
}

module "E_get_study_srp_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "E_get_study_srp"
  reserved_concurrent_executions = 50
  queues = {
    input_sqs_arn   = var.queues.D_geos_sqs.D_geos_sqs_arn
    output_sqs_arns = [var.queues.E_srps_sqs.E_srps_sqs_arn]
    dlq_arn         = var.queues.D_to_E_DLQ_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  timeout                               = var.queues.D_geos_sqs.D_geos_sqs_visibility_timeout / 2
  memory_size                           = 256
  batch_size                            = 1
}

module "F_get_study_srrs_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "F_get_study_srrs"
  reserved_concurrent_executions = 20
  queues = {
    input_sqs_arn   = var.queues.E_srps_sqs.E_srps_sqs_arn
    output_sqs_arns = [var.queues.F_srrs_sqs.F_srrs_sqs_arn]
    dlq_arn         = var.queues.E_to_F_DLQ_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  timeout                               = var.queues.E_srps_sqs.E_srps_sqs_visibility_timeout / 2
  memory_size                           = 1024
  batch_size                            = 1
}

module "G_get_srr_metadata_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "G_get_srr_metadata"
  reserved_concurrent_executions = 20
  queues = {
    input_sqs_arn   = var.queues.F_srrs_sqs.F_srrs_sqs_arn
    output_sqs_arns = [var.queues.G_srr_metadata.G_srr_metadata_arn]
    dlq_arn         = var.queues.F_to_G_DLQ_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  timeout                               = var.queues.F_srrs_sqs.F_srrs_sqs_visibility_timeout / 2
  batch_size                            = 1
}

module "H_generate_report_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "H_generate_report"
  reserved_concurrent_executions = 50
  queues = {
    input_sqs_arn   = var.queues.G_srr_metadata.G_srr_metadata_arn
    output_sqs_arns = [var.queues.H_user_feedback.H_user_feedback_arn]
    dlq_arn         = var.queues.G_to_H_DLQ_arn
  }
  s3_reports_bucket_arn                 = var.s3_reports_bucket_arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  timeout                               = var.queues.G_srr_metadata.G_srr_metadata_visibility_timeout / 2
}

module "I_send_email_lambda" {
  source                         = "./infra"
  code_path                      = "${path.module}/code"
  common_libs_layer_arn          = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                  = "I_send_email"
  reserved_concurrent_executions = 1
  queues = {
    input_sqs_arn   = var.queues.H_user_feedback.H_user_feedback_arn
    output_sqs_arns = []
    dlq_arn         = var.queues.H_to_mail_DLQ_arn
  }
  s3_reports_bucket_arn                 = var.s3_reports_bucket_arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  webmaster_mail                        = var.webmaster_mail
  timeout                               = var.queues.H_user_feedback.H_user_feedback_visibility_timeout / 2
}
