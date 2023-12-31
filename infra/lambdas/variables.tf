variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

variable "s3_bucket_id" {
  type = string
}

variable "log_level_parameter_arn" {
  type = string
}

variable "user_query_pages_sqs_arn" {
  type = string
}

variable "user_query_sqs_arn" {
  type = string
}

variable "study_ids_sqs_arn" {
  type = string
}

variable "gses_sqs_arn" {
  type = string
}

variable "gses_dlq_sqs_arn" {
  type = string
}

variable "srps_sqs_arn" {
  type = string
}

variable "srrs_sqs_arn" {
  type = string
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

variable "tags" {
  type = map(string)
}
