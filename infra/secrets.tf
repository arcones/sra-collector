resource "aws_secretsmanager_secret" "ncbi_api_key_secret" {
  name                    = "ncbi_api_key_secret"
  recovery_window_in_days = 0
}


resource "aws_secretsmanager_secret" "integration_test_credentials" {
  name                    = "integration_test_credentials"
  recovery_window_in_days = 0
}
