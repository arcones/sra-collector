module "lambdas" {
  source = "./lambdas"
  queues = {
    A_user_query_sqs = {
      A_user_query_sqs_arn                = aws_sqs_queue.A_user_query.arn,
      A_user_query_sqs_visibility_timeout = aws_sqs_queue.A_user_query.visibility_timeout_seconds
    }
    A_to_B_DLQ_arn = aws_sqs_queue.A_to_B_DLQ.arn,
    B_query_pages_sqs = {
      B_query_pages_sqs_arn                = aws_sqs_queue.B_query_pages.arn
      B_query_pages_sqs_visibility_timeout = aws_sqs_queue.B_query_pages.visibility_timeout_seconds
    },
    B_to_C_DLQ_arn = aws_sqs_queue.B_to_C_DLQ.arn,
    C_study_ids_sqs = {
      C_study_ids_sqs_arn                = aws_sqs_queue.C_study_ids.arn,
      C_study_ids_sqs_visibility_timeout = aws_sqs_queue.C_study_ids.visibility_timeout_seconds
    }
    C_to_D_DLQ_arn = aws_sqs_queue.C_to_D_DLQ.arn,
    D_geos_sqs = {
      D_geos_sqs_arn                = aws_sqs_queue.D_geos.arn
      D_geos_sqs_visibility_timeout = aws_sqs_queue.D_geos.visibility_timeout_seconds
    },
    D_to_E_DLQ_arn = aws_sqs_queue.D_to_E_DLQ.arn,
    E_srps_sqs = {
      E_srps_sqs_arn                = aws_sqs_queue.E_srps.arn
      E_srps_sqs_visibility_timeout = aws_sqs_queue.E_srps.visibility_timeout_seconds
    },
    E_to_F_DLQ_arn = aws_sqs_queue.E_to_F_DLQ.arn,
    F_srrs_sqs = {
      F_srrs_sqs_arn                = aws_sqs_queue.F_srrs.arn,
      F_srrs_sqs_visibility_timeout = aws_sqs_queue.F_srrs.visibility_timeout_seconds
    },
    F_to_G_DLQ_arn = aws_sqs_queue.F_to_G_DLQ.arn,
    G_srr_metadata = {
      G_srr_metadata_arn                = aws_sqs_queue.G_srr_metadata.arn,
      G_srr_metadata_visibility_timeout = aws_sqs_queue.G_srr_metadata.visibility_timeout_seconds
    },
    G_to_H_DLQ_arn = aws_sqs_queue.G_to_H_DLQ.arn,
    H_user_feedback = {
      H_user_feedback_arn                = aws_sqs_queue.H_user_feedback.arn,
      H_user_feedback_visibility_timeout = aws_sqs_queue.H_user_feedback.visibility_timeout_seconds
    },
    H_to_mail_DLQ_arn = aws_sqs_queue.H_to_mail_DLQ.arn
  }
  aws_apigatewayv2_api_execution_arn    = aws_apigatewayv2_api.sra_collector_api.execution_arn
  s3_code_bucket_id                     = aws_s3_bucket.sra-collector-lambdas.id
  s3_reports_bucket_arn                 = aws_s3_bucket.sra-collector-reports.arn
  ncbi_api_key_secret_arn               = aws_secretsmanager_secret.ncbi_api_key_secret.arn
  rds_kms_key_arn                       = aws_kms_key.db_kms_key.arn
  cloudwatch_to_opensearch_function_arn = module.opensearch.cloudwatch_to_opensearch_function_arn
  cognito_pool_id                       = aws_cognito_user_pool.sracollector_user_pool.id
  cognito_client_id                     = aws_cognito_user_pool_client.apigateway_cognito_client.id
  webmaster_mail                        = var.webmaster_mail
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
    "get_study_srr"     = module.lambdas.get_study_srrs_log_group_arn,
    "get_srr_metadata"  = module.lambdas.get_srr_metadata_log_group_arn,
    "generate_report"   = module.lambdas.generate_report_log_group_arn,
    "send_email"        = module.lambdas.send_email_log_group_arn
  }
}
