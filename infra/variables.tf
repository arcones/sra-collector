variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "aws_account_id" {
  type    = string
  default = "120715685161"
}

variable "tags" {
  type = map(string)
  default = {
    Application = "sra-collector"
  }
}
