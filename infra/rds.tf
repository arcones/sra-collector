resource "aws_kms_key" "db_kms_key" {
  description = "KMS for SRA collector database"
}

resource "aws_db_instance" "sra_collector_db" {
  allocated_storage             = 5
  db_name                       = "sracollector"
  engine                        = "postgres"
  engine_version                = "16.1"
  instance_class                = "db.t4g.micro"
  identifier                    = "sracollector"
  manage_master_user_password   = true
  master_user_secret_kms_key_id = aws_kms_key.db_kms_key.key_id
  username                      = "sracollector"
  db_subnet_group_name          = aws_db_subnet_group.db_subnet.name
  vpc_security_group_ids        = [aws_security_group.db_security_group.id]
  publicly_accessible           = true
  skip_final_snapshot           = true
  #  performance_insights_enabled = true
}
