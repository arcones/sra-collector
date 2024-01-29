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

variable "queues" {
  type = object({
    input_sqs_arn  = string,
    output_sqs_arn = string,
    dlq_sqs_arn    = string
  })
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
  default = 20
  type    = number
}
