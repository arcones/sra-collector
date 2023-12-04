module "user_query" {
  source                             = "./user_query"
  aws_region                         = var.aws_region
  aws_account_id                     = var.aws_account_id
  aws_apigatewayv2_api_execution_arn = var.aws_apigatewayv2_api_execution_arn
  s3_bucket_id                       = var.s3_bucket_id
  user_query_sqs_arn                 = var.user_query_sqs_arn
}
