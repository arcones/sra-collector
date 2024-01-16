variable "function_name" {
  type = string
}

variable "aws_apigatewayv2_api_execution_arn" {
  type = string
}

resource "aws_lambda_permission" "apigateway_trigger_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.aws_apigatewayv2_api_execution_arn}/*/*"
}
