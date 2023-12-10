resource "aws_lambda_function" "paginate_user_query" {
  function_name    = local.function_name
  description      = "Paginate NCBI query from the user and place results in a queue"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.paginate_user_query_s3_object.key
  role             = aws_iam_role.paginate_user_query_lambda_role.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.paginate_user_query_code.output_base64sha256
  timeout          = 30
}

resource "aws_lambda_permission" "apigateway_trigger_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.paginate_user_query.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${var.aws_apigatewayv2_api_execution_arn}/*/*"
}
