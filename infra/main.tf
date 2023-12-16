module "lambdas" {
  source                             = "./lambdas"
  aws_apigatewayv2_api_execution_arn = aws_apigatewayv2_api.sra_collector_api.execution_arn
  s3_bucket_id                       = aws_s3_bucket.lambdas.id
  user_query_sqs_arn                 = aws_sqs_queue.user_query_queue.arn
  log_level_parameter_arn            = aws_ssm_parameter.log_level.arn
  study_ids_sqs_arn                  = aws_sqs_queue.study_ids_queue.arn
  gses_sqs_arn                       = aws_sqs_queue.gses_queue.arn
  gses_dlq_sqs_arn                   = aws_sqs_queue.gses_dlq.arn
  srps_sqs_arn                       = aws_sqs_queue.srps_queue.arn
  ncbi_api_key_secret_arn            = aws_secretsmanager_secret.ncbi_api_key_secret.arn
}
