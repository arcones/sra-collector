resource "aws_apigatewayv2_api" "sra_collector_api" {
  name          = "sra_collector_api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "user_query_lambda" {
  api_id = aws_apigatewayv2_api.sra_collector_api.id

  name        = "user_query_lambda_stage"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.sra_collector_logs.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
}

resource "aws_apigatewayv2_integration" "user_query" {
  api_id             = aws_apigatewayv2_api.sra_collector_api.id
  integration_uri    = module.lambda.user_query_invoke_arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "query_study_hierarchy" {
  api_id = aws_apigatewayv2_api.sra_collector_api.id

  route_key = "GET /query-study-hierarchy"
  target    = "integrations/${aws_apigatewayv2_integration.user_query.id}"
}
