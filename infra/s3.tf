resource "aws_s3_bucket" "sra-collector-lambdas" {
  bucket = "sra-collector-lambdas"
}

resource "aws_s3_bucket" "sra-collector-reports" { # TODO add permissions to H to write here
  bucket = "sra-collector-reports"
}
