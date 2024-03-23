variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

variable "s3_bucket_id" {
  type = string
}

variable "queues" {
  type = object({
    A_user_query_sqs = object({
      A_user_query_sqs_arn                = string
      A_user_query_sqs_visibility_timeout = number
    }),
    A_DLQ_user_query_2_query_pages_arn = string,
    B_query_pages_sqs = object({
      B_query_pages_sqs_arn                = string
      B_query_pages_sqs_visibility_timeout = number
    }),
    B_DLQ_query_pages_2_study_ids_arn = string,
    C_study_ids_sqs = object({
      C_study_ids_sqs_arn                = string
      C_study_ids_sqs_visibility_timeout = number
    }),
    C_DLQ_study_ids_2_geos_arn = string,
    D_geos_sqs = object({
      D_geos_sqs_arn                = string
      D_geos_sqs_visibility_timeout = number
    }),
    D_DLQ_geos_2_srps_arn = string,
    E_srps_sqs = object({
      E_srps_sqs_arn                = string
      E_srps_sqs_visibility_timeout = number
    }),
    E_DLQ_srps_2_srrs_arn = string,
    F_srrs_sqs = object({
      F_srrs_sqs_arn                = string
      F_srrs_sqs_visibility_timeout = number
    }),
    F_DLQ_srrs_2_metadata = string
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
