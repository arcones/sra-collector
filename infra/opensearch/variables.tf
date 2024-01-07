variable "s3_bucket_id" {
  type = string
}

variable "product_log_groups" {
  type = map(string)
}

variable "tags" {
  type = map(string)
}
