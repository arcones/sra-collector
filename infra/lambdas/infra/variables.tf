variable "queues" {
  type = object({
    input_sqs_arn   = string,
    output_sqs_arns = list(string),
    dlq_arn         = string,
  })
}

variable "function_name" {
  type = string
}

variable "common_libs_layer_arn" {
  type = string
}

variable "code_path" {
  type = string
}

variable "aws_apigatewayv2_api_execution_arn" {
  default = null
  type    = string
}

variable "rds_secret_arn" {
  default = null
  type    = string
}

variable "ncbi_secret_arn" {
  default = null
  type    = string
}

variable "rds_kms_key_arn" {
  default = null
  type    = string
}

variable "cloudwatch_to_opensearch_function_arn" {
  type = string
}

variable "timeout" {
  default = 30
  type    = number
}

variable "memory_size" {
  default = 128
  type    = number
}

variable "reserved_concurrent_executions" {
  default = null
  type    = number
}

variable "batch_size" {
  default = 10
  type    = number
}

variable "batch_size_window" {
  default = 0
  type    = number
}

variable "s3_reports_bucket_arn" {
  default = null
  type    = string
}

variable "cognito_pool_id" {
  default = null
  type    = string
}

variable "cognito_client_id" {
  default = null
  type    = string
}

variable "webmaster_mail" {
  default = null
  type    = string
}
