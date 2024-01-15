variable "function_name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "common_libs_layer_arn" {
  type = string
}

variable "code_path" {
  type = string
}

variable "tags" {
  type = map(string)
}
