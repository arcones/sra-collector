module "lambda" {
  source                = "../lambda"
  code_path             = path.module
  common_libs_layer_arn = var.common_libs_layer_arn
  function_name         = basename(path.module)
  role_arn              = aws_iam_role.lambda_assume.arn
  tags                  = var.tags
}

resource "aws_lambda_permission" "apigateway_trigger_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.aws_apigatewayv2_api_execution_arn}/*/*"
}
