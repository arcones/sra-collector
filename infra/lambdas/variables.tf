variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

variable "s3_bucket_id" {
  type = string
}

variable "queues" {
  type = object({
    A_user_query_sqs_arn  = string,
    B_query_pages_sqs_arn = string,
    C_study_ids_sqs_arn   = string,
    D_gses_sqs_arn        = string,
    D_DLQ_gses_2_srps_arn = string,
    E1_srps_sqs_arn       = string,
    F_srrs_sqs_arn        = string,
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
