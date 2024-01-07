data "aws_secretsmanager_secrets" "managed_rds_secret" {
  filter {
    name   = "owning-service"
    values = ["rds"]
  }
}

locals {
  rds_secret_arn = tolist(data.aws_secretsmanager_secrets.managed_rds_secret.arns)[0]
}

module "get_user_query" {
  source                                = "./0_get_user_query"
  aws_apigatewayv2_api_execution_arn    = var.aws_apigatewayv2_api_execution_arn
  s3_bucket_id                          = var.s3_bucket_id
  user_query_sqs_arn                    = var.user_query_sqs_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "paginate_user_query" {
  source                                = "./1_paginate_user_query"
  s3_bucket_id                          = var.s3_bucket_id
  user_query_sqs_arn                    = var.user_query_sqs_arn
  user_query_pages_sqs_arn              = var.user_query_pages_sqs_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "get_study_ids" {
  source                                = "./2_get_study_ids"
  s3_bucket_id                          = var.s3_bucket_id
  user_query_pages_sqs_arn              = var.user_query_pages_sqs_arn
  study_ids_sqs_arn                     = var.study_ids_sqs_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "get_study_gse" {
  source                                = "./3_get_study_gse"
  s3_bucket_id                          = var.s3_bucket_id
  study_ids_sqs_arn                     = var.study_ids_sqs_arn
  gses_sqs_arn                          = var.gses_sqs_arn
  ncbi_api_key_secret_arn               = var.ncbi_api_key_secret_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "get_study_srp" {
  source                                = "./4_get_study_srp"
  s3_bucket_id                          = var.s3_bucket_id
  gses_sqs_arn                          = var.gses_sqs_arn
  srps_sqs_arn                          = var.srps_sqs_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = tolist(data.aws_secretsmanager_secrets.managed_rds_secret.arns)[0]
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "dlq_get_srp_pysradb_error" {
  source                                = "./4_dlq_get_srp_pysradb_error"
  s3_bucket_id                          = var.s3_bucket_id
  gses_dlq_sqs_arn                      = var.gses_dlq_sqs_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "get_study_srrs" {
  source                                = "./5_get_study_srrs"
  s3_bucket_id                          = var.s3_bucket_id
  srps_sqs_arn                          = var.srps_sqs_arn
  srrs_sqs_arn                          = var.srrs_sqs_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}
