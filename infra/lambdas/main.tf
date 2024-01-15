data "aws_secretsmanager_secrets" "managed_rds_secret" {
  filter {
    name   = "owning-service"
    values = ["rds"]
  }
}

locals {
  rds_secret_arn = tolist(data.aws_secretsmanager_secrets.managed_rds_secret.arns)[0]
}

module "A_get_user_query" {
  source                             = "./A_get-user-query"
  aws_apigatewayv2_api_execution_arn = var.aws_apigatewayv2_api_execution_arn
  #  s3_bucket_id                          = var.s3_bucket_id
  user_query_sqs_arn      = var.user_query_sqs_arn
  log_level_parameter_arn = var.log_level_parameter_arn
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  #  common_libs_layer_version = aws_lambda_layer_version.common_libs_lambda_layer.version
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "B_paginate_user_query" {
  source = "./B_paginate-user-query"
  #  s3_bucket_id                          = var.s3_bucket_id
  user_query_sqs_arn                    = var.user_query_sqs_arn
  user_query_pages_sqs_arn              = var.user_query_pages_sqs_arn
  log_level_parameter_arn               = var.log_level_parameter_arn
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  common_libs_layer_version             = aws_lambda_layer_version.common_libs_lambda_layer.version
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "C_get_study_ids" {
  source = "./C_get-study-ids"
  #  s3_bucket_id                          = var.s3_bucket_id
  user_query_pages_sqs_arn = var.user_query_pages_sqs_arn
  study_ids_sqs_arn        = var.study_ids_sqs_arn
  log_level_parameter_arn  = var.log_level_parameter_arn
  common_libs_layer_arn    = aws_lambda_layer_version.common_libs_lambda_layer.arn
  #  common_libs_layer_version = aws_lambda_layer_version.common_libs_lambda_layer.version
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "D_get_study_gse" {
  source = "./D_get-study-gse"
  #  s3_bucket_id                          = var.s3_bucket_id
  study_ids_sqs_arn       = var.study_ids_sqs_arn
  gses_sqs_arn            = var.gses_sqs_arn
  ncbi_api_key_secret_arn = var.ncbi_api_key_secret_arn
  log_level_parameter_arn = var.log_level_parameter_arn
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  #  common_libs_layer_version = aws_lambda_layer_version.common_libs_lambda_layer.version
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "E1_get_study_srp" {
  source = "./E1_get-study-srp"
  #  s3_bucket_id                          = var.s3_bucket_id
  gses_sqs_arn            = var.gses_sqs_arn
  srps_sqs_arn            = var.srps_sqs_arn
  log_level_parameter_arn = var.log_level_parameter_arn
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  #  common_libs_layer_version = aws_lambda_layer_version.common_libs_lambda_layer.version
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = tolist(data.aws_secretsmanager_secrets.managed_rds_secret.arns)[0]
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "E2_dlq_get_srp_pysradb_error" {
  source = "./E2_dlq-get-srp-pysradb-error"
  #  s3_bucket_id                          = var.s3_bucket_id
  gses_dlq_sqs_arn        = var.gses_dlq_sqs_arn
  log_level_parameter_arn = var.log_level_parameter_arn
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  #  common_libs_layer_version = aws_lambda_layer_version.common_libs_lambda_layer.version
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "F_get_study_srrs" {
  source = "./F_get-study-srrs"
  #  s3_bucket_id                          = var.s3_bucket_id
  srps_sqs_arn            = var.srps_sqs_arn
  srrs_sqs_arn            = var.srrs_sqs_arn
  log_level_parameter_arn = var.log_level_parameter_arn
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  #  common_libs_layer_version = aws_lambda_layer_version.common_libs_lambda_layer.version
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}
