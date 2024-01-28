terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.34.0"
    }
  }

  backend "s3" {
    acl     = "bucket-owner-full-control"
    bucket  = "sra-collector-infra-metadata"
    region  = "eu-central-1"
    key     = "dev/terraform.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}
