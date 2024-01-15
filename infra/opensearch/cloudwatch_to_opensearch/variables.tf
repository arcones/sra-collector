variable "domain_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}

variable "product_log_groups" {
  type = map(string)
}
