module "lambdas" {
  source                             = "./lambdas"
  aws_region                         = var.aws_region
  aws_account_id                     = var.aws_account_id
  aws_apigatewayv2_api_execution_arn = aws_apigatewayv2_api.sra_collector_api.execution_arn
  s3_bucket_id                       = aws_s3_bucket.lambdas.id
  user_query_sqs_arn                 = aws_sqs_queue.user_query_queue.arn
  log_level_parameter_arn            = aws_ssm_parameter.log_level.arn
  study_ids_sqs_arn                  = aws_sqs_queue.study_ids_queue.arn
  #  study_summaries_sqs_arn            = aws_sqs_queue.study_summaries_queue.arn
  #  pending_srp_sqs_arn                = aws_sqs_queue.pending_srp_queue.arn
  #  ncbi_api_key_secret_arn            = aws_secretsmanager_secret.ncbi_api_key.arn
}
