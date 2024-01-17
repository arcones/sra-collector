resource "random_uuid" "lambda_code_hash" {
  keepers = {
    for filename in setunion(
      fileset("python3", "*.py")
    ) : filename => filemd5(filename)
  }
}

data "archive_file" "code" {
  type        = "zip"
  source_file = "${var.code_path}/${var.function_name}.py"
  output_path = ".tmp/${random_uuid.lambda_code_hash.result}.zip"
}

resource "aws_lambda_function" "function" {
  function_name    = var.function_name
  filename         = data.archive_file.code.output_path
  handler          = "${var.function_name}.handler"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.11"
  layers           = [var.common_libs_layer_arn]
  timeout          = 10
  source_code_hash = data.archive_file.code.output_base64sha256
  tags             = var.tags
}

resource "aws_lambda_permission" "apigateway_trigger_lambda_permission" {
  count         = var.input_sqs_arn == null ? 1 : 0
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.aws_apigatewayv2_api_execution_arn}/*/*"
}


resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  count            = var.input_sqs_arn == null ? 0 : 1
  event_source_arn = var.input_sqs_arn
  enabled          = true
  function_name    = var.function_name
  batch_size       = 1
}
