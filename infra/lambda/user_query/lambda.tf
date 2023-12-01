resource "aws_lambda_function" "user_query" {
  function_name    = var.lambda_name
  description      = "Receives & processes NCBI query from the user. It fetches study IDs and send them to queue"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.lambda_user_query.key
  role             = aws_iam_role.user_query_lambda_role.arn
  handler          = "${var.lambda_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.lambda_user_query.output_base64sha256
}

resource "aws_lambda_permission" "lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.user_query.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${var.aws_apigatewayv2_api_execution_arn}/*/*"
}
