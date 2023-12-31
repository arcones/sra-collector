resource "aws_lambda_function" "get_user_query" {
  function_name = local.function_name
  description   = "Get NCBI query from the user and place it in a queue"
  s3_bucket     = var.s3_bucket_id
  s3_key        = aws_s3_object.get_user_query_s3_object.key
  role          = aws_iam_role.lambda_assume.arn
  handler       = "${local.function_name}.handler"
  runtime       = "python3.11"
  layers        = [var.common_libs_layer_arn]
  timeout       = 30
  lifecycle {
    replace_triggered_by = [null_resource.code_watcher]
  }
  tags = var.tags
}

resource "null_resource" "code_watcher" {
  triggers = {
    dir_sha1 = sha1(join("", [for file in fileset(local.code_folder, "*") : filesha1("${local.code_folder}/${file}")]))
  }
}

resource "aws_lambda_permission" "apigateway_trigger_lambda_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_user_query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.aws_apigatewayv2_api_execution_arn}/*/*"
}
