resource "aws_s3_bucket" "sra-collector-lambdas" {
  bucket = "sra-collector-lambdas"
}

resource "aws_s3_bucket" "sra-collector-reports" {
  bucket = "sra-collector-reports"
}

resource "aws_s3_bucket" "integration-tests-s3" {
  bucket = "integration-tests-s3"
}
