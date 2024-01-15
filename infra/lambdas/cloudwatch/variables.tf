variable "function_name" {
  type = string
}

variable "cloudwatch_to_opensearch_function_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}
