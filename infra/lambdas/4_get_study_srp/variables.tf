variable "s3_bucket_id" {
  type = string
}

variable "gses_sqs_arn" {
  type = string
}

variable "srps_sqs_arn" {
  type = string
}

variable "log_level_parameter_arn" {
  type = string
}

variable "common_libs_layer_arn" {
  type = string
}

variable "rds_kms_key_arn" {
  type = string
}

variable "rds_secret_arn" {
  type = string
}

variable "cloudwatch_to_opensearch_function_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}
