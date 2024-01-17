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
  source                                = "./infra"
  code_path                             = "${path.module}/code"
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                         = "A_get_user_query"
  log_level_parameter_arn               = var.log_level_parameter_arn
  output_sqs_arn                        = var.user_query_sqs_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  aws_apigatewayv2_api_execution_arn    = var.aws_apigatewayv2_api_execution_arn
  tags                                  = var.tags
}

module "B_paginate_user_query_lambda" {
  source                                = "./infra"
  code_path                             = "${path.module}/code"
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                         = "B_paginate_user_query"
  log_level_parameter_arn               = var.log_level_parameter_arn
  input_sqs_arn                         = var.user_query_sqs_arn
  output_sqs_arn                        = var.user_query_pages_sqs_arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "C_get_study_ids_lambda" {
  source                                = "./infra"
  code_path                             = "${path.module}/code"
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                         = "C_get_study_ids"
  log_level_parameter_arn               = var.log_level_parameter_arn
  input_sqs_arn                         = var.user_query_pages_sqs_arn
  output_sqs_arn                        = var.study_ids_sqs_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "D_get_study_gse_lambda" {
  source                                = "./infra"
  code_path                             = "${path.module}/code"
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                         = "D_get_study_gse"
  log_level_parameter_arn               = var.log_level_parameter_arn
  input_sqs_arn                         = var.study_ids_sqs_arn
  output_sqs_arn                        = var.gses_sqs_arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  ncbi_secret_arn                       = var.ncbi_api_key_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "E1_get_study_srp_lambda" {
  source                                = "./infra"
  code_path                             = "${path.module}/code"
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                         = "E1_get_study_srp"
  log_level_parameter_arn               = var.log_level_parameter_arn
  input_sqs_arn                         = var.gses_sqs_arn
  output_sqs_arn                        = var.srps_sqs_arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "E2_dlq_get_srp_pysradb_error_lambda" {
  source                                = "./infra"
  code_path                             = "${path.module}/code"
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                         = "E2_dlq_get_srp_pysradb_error"
  log_level_parameter_arn               = var.log_level_parameter_arn
  input_sqs_arn                         = var.gses_dlq_sqs_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "F_get_study_srrs_lambda" {
  source                                = "./infra"
  code_path                             = "${path.module}/code"
  common_libs_layer_arn                 = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name                         = "F_get_study_srrs"
  log_level_parameter_arn               = var.log_level_parameter_arn
  input_sqs_arn                         = var.srps_sqs_arn
  output_sqs_arn                        = var.srrs_sqs_arn
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}
