module "user_query" {
  source                             = "./user_query"
  aws_region                         = var.aws_region
  aws_account_id                     = var.aws_account_id
  aws_apigatewayv2_api_execution_arn = var.aws_apigatewayv2_api_execution_arn
  s3_bucket_id                       = var.s3_bucket_id
  study_ids_sqs_arn                  = var.study_ids_sqs_arn
}

module "study_summaries" {
  source                  = "./study_summaries"
  aws_region              = var.aws_region
  aws_account_id          = var.aws_account_id
  s3_bucket_id            = var.s3_bucket_id
  study_ids_sqs_arn       = var.study_ids_sqs_arn
  study_summaries_sqs_arn = var.study_summaries_sqs_arn
  ncbi_api_key_secret_arn = var.ncbi_api_key_secret_arn
}
