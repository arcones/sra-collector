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
    input_sqs_arn  = null
    output_sqs_arn = var.queues.A_user_query_sqs_arn
    dlq_arn        = null
  }
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  aws_apigatewayv2_api_execution_arn    = var.aws_apigatewayv2_api_execution_arn
}

module "B_get_query_pages_lambda" {
  source                = "./infra"
  code_path             = "${path.module}/code"
  common_libs_layer_arn = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name         = "B_get_query_pages"
  queues = {
    input_sqs_arn  = var.queues.A_user_query_sqs_arn
    output_sqs_arn = var.queues.B_query_pages_sqs_arn
    dlq_arn        = var.queues.A_DLQ_user_query_2_query_pages_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
}

module "C_get_study_ids_lambda" {
  source                = "./infra"
  code_path             = "${path.module}/code"
  common_libs_layer_arn = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name         = "C_get_study_ids"
  queues = {
    input_sqs_arn  = var.queues.B_query_pages_sqs_arn
    output_sqs_arn = var.queues.C_study_ids_sqs_arn
    dlq_arn        = var.queues.B_DLQ_query_pages_2_study_ids_arn
  }
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
}

module "D_get_study_gse_lambda" {
  source                = "./infra"
  code_path             = "${path.module}/code"
  common_libs_layer_arn = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name         = "D_get_study_gse"
  queues = {
    input_sqs_arn  = var.queues.C_study_ids_sqs_arn
    output_sqs_arn = var.queues.D_gses_sqs_arn
    dlq_arn        = var.queues.C_DLQ_study_ids_2_gses_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  ncbi_secret_arn                       = var.ncbi_api_key_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
}

module "E_get_study_srp_lambda" {
  source                = "./infra"
  code_path             = "${path.module}/code"
  common_libs_layer_arn = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name         = "E_get_study_srp"
  queues = {
    input_sqs_arn  = var.queues.D_gses_sqs_arn
    output_sqs_arn = var.queues.E_srps_sqs_arn
    dlq_arn        = var.queues.D_DLQ_gses_2_srps_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
}

module "F_get_study_srrs_lambda" {
  source                = "./infra"
  code_path             = "${path.module}/code"
  common_libs_layer_arn = aws_lambda_layer_version.common_libs_lambda_layer.arn
  function_name         = "F_get_study_srrs"
  queues = {
    input_sqs_arn  = var.queues.E_srps_sqs_arn
    output_sqs_arn = var.queues.F_srrs_sqs_arn
    dlq_arn        = var.queues.E_DLQ_srps_2_srrs_arn
  }
  rds_kms_key_arn                       = var.rds_kms_key_arn
  rds_secret_arn                        = local.rds_secret_arn
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
}
