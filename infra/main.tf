module "lambdas" {
  source                                = "./lambdas"
  aws_apigatewayv2_api_execution_arn    = aws_apigatewayv2_api.sra_collector_api.execution_arn
  s3_bucket_id                          = aws_s3_bucket.lambdas.id
  user_query_pages_sqs_arn              = aws_sqs_queue.user_query_pages_queue.arn
  log_level_parameter_arn               = aws_ssm_parameter.log_level.arn
  user_query_sqs_arn                    = aws_sqs_queue.user_query_queue.arn
  study_ids_sqs_arn                     = aws_sqs_queue.study_ids_queue.arn
  gses_sqs_arn                          = aws_sqs_queue.gses_queue.arn
  gses_dlq_sqs_arn                      = aws_sqs_queue.gses_dlq.arn
  srps_sqs_arn                          = aws_sqs_queue.srps_queue.arn
  srrs_sqs_arn                          = aws_sqs_queue.srrs_queue.arn
  ncbi_api_key_secret_arn               = aws_secretsmanager_secret.ncbi_api_key_secret.arn
  rds_kms_key_arn                       = aws_kms_key.db_kms_key.arn
  cloudwatch_to_opensearch_function_arn = module.opensearch.cloudwatch_to_opensearch_function_arn
  tags                                  = var.tags
}

module "opensearch" {
  source       = "./opensearch"
  s3_bucket_id = aws_s3_bucket.lambdas.id
  product_log_groups = {
    "sra_collector_api"         = aws_cloudwatch_log_group.sra_collector_logs.arn,
    "get_user_query"            = module.lambdas.get_user_query_log_group_arn,
    "paginate_user_query"       = module.lambdas.paginate_user_query_log_group_arn,
    "get_study_ids"             = module.lambdas.get_study_ids_log_group_arn,
    "get_study_gse"             = module.lambdas.get_study_gse_log_group_arn,
    "dlq_get_srp_pysradb_error" = module.lambdas.dlq_get_srp_pysradb_error_log_group_arn,
    "get_study_srp"             = module.lambdas.get_study_srp_log_group_arn,
    "get_study_srr"             = module.lambdas.get_study_srrs_log_group_arn
  }
  tags = var.tags
}
