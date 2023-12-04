module "lambda" {
  source                             = "./lambda"
  aws_region                         = var.aws_region
  aws_account_id                     = var.aws_account_id
  aws_apigatewayv2_api_execution_arn = aws_apigatewayv2_api.sra_collector_api.execution_arn
  s3_bucket_id                       = aws_s3_bucket.lambdas.id
  user_query_sqs_arn                 = aws_sqs_queue.user_query_queue.arn
}
