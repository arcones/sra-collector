variable "aws_region" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "s3_bucket_id" {
  type = string
}

variable "pending_srp_sqs_arn" {
  type = string
}

variable "study_summaries_sqs_arn" {
  type = string
}

variable "pysradb_lambda_layer" {
  type = string
}
