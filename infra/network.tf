data "aws_availability_zones" "available" {}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.1"

  name                 = "sra_collector_vpc"
  cidr                 = "10.0.0.0/16"
  azs                  = data.aws_availability_zones.available.names
  public_subnets       = ["10.0.4.0/24", "10.0.5.0/24", "10.0.6.0/24"]
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_db_subnet_group" "db_subnet" {
  name       = "db_subnet"
  subnet_ids = module.vpc.public_subnets
}

resource "aws_security_group" "db_security_group" {
  name   = "db_security_group"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
