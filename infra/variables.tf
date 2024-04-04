variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "aws_account_id" {
  type    = string
  default = "120715685161"
}

variable "webmaster_mail" {
  type    = string
  default = "marta.arcones@gmail.com"
}

variable "subdomain" {
  type    = string
  default = "martaarcones.net"
}

data "aws_route53_zone" "zone" {
  name         = var.subdomain
  private_zone = false
}
