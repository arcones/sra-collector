variable "s3_bucket_id" {
  type = string
}

variable "domain_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}

variable "product_log_groups" {
  type = map(string)
}
