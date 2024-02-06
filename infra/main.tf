module "lambdas" {
  source                             = "./lambdas"
  aws_apigatewayv2_api_execution_arn = aws_apigatewayv2_api.sra_collector_api.execution_arn
  s3_bucket_id                       = aws_s3_bucket.lambdas.id
  queues = {
    A_user_query_sqs_arn  = aws_sqs_queue.A_user_query.arn,
    B_query_pages_sqs_arn = aws_sqs_queue.B_query_pages.arn,
    C_study_ids_sqs_arn   = aws_sqs_queue.C_study_ids.arn,
    D_gses_sqs_arn        = aws_sqs_queue.D_gses.arn,
    D_DLQ_gses_2_srps_arn = aws_sqs_queue.D_DLQ_gses_2_srps.arn,
    E1_srps_sqs_arn       = aws_sqs_queue.E1_srps.arn,
    F_srrs_sqs_arn        = aws_sqs_queue.F_srrs.arn,
  }
  ncbi_api_key_secret_arn               = aws_secretsmanager_secret.ncbi_api_key_secret.arn
  rds_kms_key_arn                       = aws_kms_key.db_kms_key.arn
  cloudwatch_to_opensearch_function_arn = module.opensearch.cloudwatch_to_opensearch_function_arn
}

module "opensearch" {
  source = "./opensearch"
  product_log_groups = {
    "sra_collector_api"         = aws_cloudwatch_log_group.sra_collector_logs.arn,
    "get_user_query"            = module.lambdas.get_user_query_log_group_arn,
    "get_query_pages"           = module.lambdas.get_query_pages_log_group_arn,
    "get_study_ids"             = module.lambdas.get_study_ids_log_group_arn,
    "get_study_gse"             = module.lambdas.get_study_gse_log_group_arn,
    "dlq_get_srp_pysradb_error" = module.lambdas.dlq_get_srp_pysradb_error_log_group_arn,
    "get_study_srp"             = module.lambdas.get_study_srp_log_group_arn,
    "get_study_srr"             = module.lambdas.get_study_srrs_log_group_arn
  }
}
