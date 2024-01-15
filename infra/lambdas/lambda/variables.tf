variable "function_name" {
  type = string
}

variable "common_libs_layer_arn" {
  type = string
}

variable "code_path" {
  type = string
}

variable "log_level_parameter_arn" {
  type = string
}

variable "input_sqs_arn" {
  default = null
  type    = string
}

variable "output_sqs_arn" {
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

variable "tags" {
  type = map(string)
}
