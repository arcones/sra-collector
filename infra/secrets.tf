resource "aws_secretsmanager_secret" "ncbi_api_key_secret" {
  name                    = "ncbi_api_key_secret"
  recovery_window_in_days = 0
}
