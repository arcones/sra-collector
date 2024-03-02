module "lambdas" {
  source                             = "./lambdas"
  aws_apigatewayv2_api_execution_arn = aws_apigatewayv2_api.sra_collector_api.execution_arn
  s3_bucket_id                       = aws_s3_bucket.lambdas.id
  queues = {
    A_user_query_sqs = {
      A_user_query_sqs_arn                = aws_sqs_queue.A_user_query.arn,
      A_user_query_sqs_visibility_timeout = aws_sqs_queue.A_user_query.visibility_timeout_seconds
    }
    A_DLQ_user_query_2_query_pages_arn = aws_sqs_queue.A_DLQ_user_query_2_query_pages.arn,
    B_query_pages_sqs = {
      B_query_pages_sqs_arn                = aws_sqs_queue.B_query_pages.arn
      B_query_pages_sqs_visibility_timeout = aws_sqs_queue.B_query_pages.visibility_timeout_seconds
    },
    B_DLQ_query_pages_2_study_ids_arn = aws_sqs_queue.B_DLQ_query_pages_2_study_ids.arn,
    C_study_ids_sqs = {
      C_study_ids_sqs_arn                = aws_sqs_queue.C_study_ids.arn,
      C_study_ids_sqs_visibility_timeout = aws_sqs_queue.C_study_ids.visibility_timeout_seconds
    }
    C_DLQ_study_ids_2_geos_arn = aws_sqs_queue.C_DLQ_study_ids_2_geos.arn,
    D_geos_sqs = {
      D_geos_sqs_arn                = aws_sqs_queue.D_geos.arn
      D_geos_sqs_visibility_timeout = aws_sqs_queue.D_geos.visibility_timeout_seconds
    },
    D_DLQ_geos_2_srps_arn = aws_sqs_queue.D_DLQ_geos_2_srps.arn,
    E_srps_sqs = {
      E_srps_sqs_arn                = aws_sqs_queue.E_srps.arn
      E_srps_sqs_visibility_timeout = aws_sqs_queue.E_srps.visibility_timeout_seconds
    },
    E_DLQ_srps_2_srrs_arn = aws_sqs_queue.E_DLQ_srps_2_srrs.arn,
    F_srrs_sqs = {
      F_srrs_sqs_arn                = aws_sqs_queue.F_srrs.arn,
      F_srrs_sqs_visibility_timeout = aws_sqs_queue.F_srrs.visibility_timeout_seconds
    }
  }
  ncbi_api_key_secret_arn               = aws_secretsmanager_secret.ncbi_api_key_secret.arn
  rds_kms_key_arn                       = aws_kms_key.db_kms_key.arn
  cloudwatch_to_opensearch_function_arn = module.opensearch.cloudwatch_to_opensearch_function_arn
}

module "opensearch" {
  source = "./opensearch"
  product_log_groups = {
    "sra_collector_api" = aws_cloudwatch_log_group.sra_collector_logs.arn,
    "get_user_query"    = module.lambdas.get_user_query_log_group_arn,
    "get_query_pages"   = module.lambdas.get_query_pages_log_group_arn,
    "get_study_ids"     = module.lambdas.get_study_ids_log_group_arn,
    "get_study_geo"     = module.lambdas.get_study_geo_log_group_arn,
    "get_study_srp"     = module.lambdas.get_study_srp_log_group_arn,
    "get_study_srr"     = module.lambdas.get_study_srrs_log_group_arn
  }
}
