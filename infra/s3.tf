resource "aws_s3_bucket" "lambdas" {
  bucket = "sra-collector-lambdas"
  tags   = var.tags
}
