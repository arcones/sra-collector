resource "aws_cognito_user_pool" "sracollector_user_pool" {
  name                     = "sra-collector-user-pool"
  deletion_protection      = "ACTIVE"
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  username_configuration {
    case_sensitive = false
  }
}

resource "aws_cognito_user_pool_domain" "cognito_domain" {
  domain       = "sracollector-user-pool"
  user_pool_id = aws_cognito_user_pool.sracollector_user_pool.id
}

resource "aws_cognito_user_pool_client" "apigateway_cognito_client" {
  name                   = "OpenAPI"
  user_pool_id           = aws_cognito_user_pool.sracollector_user_pool.id
  explicit_auth_flows    = ["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_PASSWORD_AUTH"]
  refresh_token_validity = 1
  access_token_validity  = 60
  id_token_validity      = 60
  token_validity_units {
    refresh_token = "days"
    access_token  = "minutes"
    id_token      = "minutes"
  }
}
