resource "aws_apigatewayv2_api" "sra_collector_api" {
  name          = "sra_collector_api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["https://arcones.github.io"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type", "username", "password"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_stage" "apigw_stage" {
  api_id = aws_apigatewayv2_api.sra_collector_api.id

  name        = "api"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.sra_collector_logs.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      httpMethod              = "$context.httpMethod"
      path                    = "$context.path"
      status                  = "$context.status"
      sourceIp                = "$context.identity.sourceIp"
      userAgent               = "$context.identity.userAgent",
      responseLatency         = "$context.responseLatency"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }
}

resource "aws_apigatewayv2_integration" "get_user_query" {
  api_id                 = aws_apigatewayv2_api.sra_collector_api.id
  integration_uri        = module.lambdas.get_user_query_invoke_arn
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "query_study_hierarchy" {
  api_id    = aws_apigatewayv2_api.sra_collector_api.id
  route_key = "POST /query-submit"
  target    = "integrations/${aws_apigatewayv2_integration.get_user_query.id}"
}

resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = aws_apigatewayv2_api.sra_collector_api.id
  domain_name = aws_apigatewayv2_domain_name.apigateway_domain_name.id
  stage       = aws_apigatewayv2_stage.apigw_stage.id
}
