module "paginate_user_query" {
  source                             = "./1_paginate_user_query"
  aws_region                         = var.aws_region
  aws_account_id                     = var.aws_account_id
  aws_apigatewayv2_api_execution_arn = var.aws_apigatewayv2_api_execution_arn
  s3_bucket_id                       = var.s3_bucket_id
  user_query_sqs_arn                 = var.user_query_sqs_arn
  log_level_parameter_arn            = var.log_level_parameter_arn
}

module "get_study_ids" {
  source                  = "./2_get_study_ids"
  aws_region              = var.aws_region
  aws_account_id          = var.aws_account_id
  s3_bucket_id            = var.s3_bucket_id
  user_query_sqs_arn      = var.user_query_sqs_arn
  study_ids_sqs_arn       = var.study_ids_sqs_arn
  log_level_parameter_arn = var.log_level_parameter_arn
}

module "study_summaries" {
  source                  = "./3_get_study_gse"
  aws_region              = var.aws_region
  aws_account_id          = var.aws_account_id
  s3_bucket_id            = var.s3_bucket_id
  study_ids_sqs_arn       = var.study_ids_sqs_arn
  gses_sqs_arn            = var.gses_sqs_arn
  ncbi_api_key_secret_arn = var.ncbi_api_key_secret_arn
  log_level_parameter_arn = var.log_level_parameter_arn
}

#module "missing_srps" {
#  source                  = "./missing_srps"
#  aws_region              = var.aws_region
#  aws_account_id          = var.aws_account_id
#  s3_bucket_id            = var.s3_bucket_id
#  pending_srp_sqs_arn     = var.pending_srp_sqs_arn
#  study_summaries_sqs_arn = var.study_summaries_sqs_arn
#  pysradb_lambda_layer    = aws_lambda_layer_version.missing_srps_lambda_layer.arn
#}
