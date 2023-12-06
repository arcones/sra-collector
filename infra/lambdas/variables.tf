variable "aws_region" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

variable "s3_bucket_id" {
  type = string
}

variable "study_ids_sqs_arn" {
  type = string
}

variable "study_summaries_sqs_arn" {
  type = string
}

variable "pending_srp_sqs_arn" {
  type = string
}

variable "ncbi_api_key_secret_arn" {
  type = string
}
