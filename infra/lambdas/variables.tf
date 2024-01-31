variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

variable "s3_bucket_id" {
  type = string
}

variable "queues" {
  type = object({
    user_query_pages_sqs_arn = string,
    user_query_pages_dlq_arn = string,
    user_query_sqs_arn       = string,
    user_query_dlq_arn       = string,
    study_ids_sqs_arn        = string,
    study_ids_dlq_arn        = string,
    gses_sqs_arn             = string,
    gses_dlq_arn             = string,
    srps_sqs_arn             = string,
    srps_dlq_arn             = string,
    srrs_sqs_arn             = string,
    srrs_dlq_arn             = string
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
