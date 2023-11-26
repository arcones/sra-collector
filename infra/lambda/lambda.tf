resource "aws_lambda_function" "user_query" {
  filename         = "user-query.zip"
  function_name    = "user-query"
  role             = aws_iam_role.user_query_lambda_role.arn
  handler          = "lambda.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("user-query.zip")
}

resource "aws_lambda_permission" "lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.user_query.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${var.aws_apigatewayv2_api_execution_arn}/*/*"
}