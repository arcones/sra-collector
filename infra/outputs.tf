output "base_url" {
  value = aws_apigatewayv2_stage.user_query_lambda.invoke_url
}
