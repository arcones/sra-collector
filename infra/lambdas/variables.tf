variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

variable "s3_bucket_id" {
  type = string
}

variable "queues" {
  type = object({
    A_user_query_sqs_arn               = string,
    A_DLQ_user_query_2_query_pages_arn = string,
    B_query_pages_sqs_arn              = string,
    B_DLQ_query_pages_2_study_ids_arn  = string,
    C_study_ids_sqs_arn                = string,
    C_DLQ_study_ids_2_gses_arn         = string,
    D_gses_sqs_arn                     = string,
    D_DLQ_gses_2_srps_arn              = string,
    E_srps_sqs_arn                     = string,
    E_DLQ_srps_2_srrs_arn              = string,
    F_srrs_sqs_arn                     = string,
  })
}

variable "ncbi_api_key_secret_arn" {
  type = string
}

variable "rds_kms_key_arn" {
  type = string
}

variable "cloudwatch_to_opensearch_function_arn" {
  type = string
}
