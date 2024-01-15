variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

#variable "s3_bucket_id" {
#  type = string
#}

variable "user_query_sqs_arn" {
  type = string
}

variable "log_level_parameter_arn" {
  type = string
}

variable "common_libs_layer_arn" {
  type = string
}

variable "cloudwatch_to_opensearch_function_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}
#
#variable "common_libs_layer_version" {
#  type = number
#}
