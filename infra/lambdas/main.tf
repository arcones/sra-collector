data "aws_secretsmanager_secrets" "managed_rds_secret" {
  filter {
    name   = "owning-service"
    values = ["rds"]
  }
}

locals {
  rds_secret_arn = tolist(data.aws_secretsmanager_secrets.managed_rds_secret.arns)[0]
}

module "A_get-user-query-lambda" {
  source                  = "./lambda"
  code_path               = "${path.module}/code/A_get-user-query"
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name           = "A_get-user-query"
  log_level_parameter_arn = var.log_level_parameter_arn
  output_sqs_arn          = var.user_query_sqs_arn
  tags                    = var.tags
}

module "A_get-user-query-cloudwatch" {
  source                                = "./cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = "A_get-user-query"
  tags                                  = var.tags
}

module "A_get_user_query-extra-config" {
  source                             = "./code/A_get-user-query"
  function_name                      = "A_get-user-query"
  aws_apigatewayv2_api_execution_arn = var.aws_apigatewayv2_api_execution_arn
}

module "B_paginate_user_query-lambda" {
  source                  = "./lambda"
  code_path               = "${path.module}/code/B_paginate-user-query"
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name           = "B_paginate-user-query"
  log_level_parameter_arn = var.log_level_parameter_arn
  input_sqs_arn           = var.user_query_sqs_arn
  output_sqs_arn          = var.user_query_pages_sqs_arn
  rds_kms_key_arn         = var.rds_kms_key_arn
  rds_secret_arn          = local.rds_secret_arn
  tags                    = var.tags
}

module "B_paginate_user_query-cloudwatch" {
  source                                = "./cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = "B_paginate-user-query"
  tags                                  = var.tags
}
//TODO quorum around - and _

module "C_get-study-ids-lambda" {
  source                  = "./lambda"
  code_path               = "${path.module}/code/C_get-study-ids"
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name           = "C_get-study-ids"
  log_level_parameter_arn = var.log_level_parameter_arn
  input_sqs_arn           = var.user_query_pages_sqs_arn
  output_sqs_arn          = var.study_ids_sqs_arn
  tags                    = var.tags
}

module "C_get-study-ids-cloudwatch" {
  source                                = "./cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = "C_get-study-ids"
  tags                                  = var.tags
}

module "D_get-study-gse-lambda" {
  source                  = "./lambda"
  code_path               = "${path.module}/code/D_get-study-gse"
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name           = "D_get-study-gse"
  log_level_parameter_arn = var.log_level_parameter_arn
  input_sqs_arn           = var.study_ids_sqs_arn
  output_sqs_arn          = var.gses_sqs_arn
  rds_kms_key_arn         = var.rds_kms_key_arn
  rds_secret_arn          = local.rds_secret_arn
  ncbi_secret_arn         = var.ncbi_api_key_secret_arn
  tags                    = var.tags
}

module "D_get-study-gse-cloudwatch" {
  source                                = "./cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = "D_get-study-gse"
  tags                                  = var.tags
}

module "E1_get-study-srp-lambda" {
  source                  = "./lambda"
  code_path               = "${path.module}/code/E1_get-study-srp"
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name           = "E1_get-study-srp"
  log_level_parameter_arn = var.log_level_parameter_arn
  input_sqs_arn           = var.gses_sqs_arn
  output_sqs_arn          = var.srps_sqs_arn
  rds_kms_key_arn         = var.rds_kms_key_arn
  rds_secret_arn          = local.rds_secret_arn
  tags                    = var.tags
}

module "E1_get-study-srp-cloudwatch" {
  source                                = "./cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = "E1_get-study-srp"
  tags                                  = var.tags
}

module "E2_dlq-get-srp-pysradb-error-lambda" {
  source                  = "./lambda"
  code_path               = "${path.module}/code/E2_dlq-get-srp-pysradb-error"
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name           = "E2_dlq-get-srp-pysradb-error"
  log_level_parameter_arn = var.log_level_parameter_arn
  input_sqs_arn           = var.gses_dlq_sqs_arn
  tags                    = var.tags
}

module "E2_dlq-get-srp-pysradb-error-cloudwatch" {
  source                                = "./cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = "E2_dlq-get-srp-pysradb-error"
  tags                                  = var.tags
}

module "F_get-study-srrs-lambda" {
  source                  = "./lambda"
  code_path               = "${path.module}/code/F_get-study-srrs"
  common_libs_layer_arn   = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name           = "F_get-study-srrs"
  log_level_parameter_arn = var.log_level_parameter_arn
  input_sqs_arn           = var.srps_sqs_arn
  output_sqs_arn          = var.srrs_sqs_arn
  rds_kms_key_arn         = var.rds_kms_key_arn
  rds_secret_arn          = local.rds_secret_arn
  tags                    = var.tags
}

module "F_get-study-srrs-cloudwatch" {
  source                                = "./cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = "F_get-study-srrs"
  tags                                  = var.tags
}
