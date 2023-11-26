resource "aws_cloudwatch_log_group" "sra_collector_logs" {
  name              = "/aws/api_gateway/${aws_apigatewayv2_api.sra_collector_api.name}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "user_query_logs" {
  name              = "/aws/lambda/${module.lambda.user_query_function_name}"
  retention_in_days = 30
}