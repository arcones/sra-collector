resource "random_uuid" "lambda_code_hash" {
  keepers = {
    for filename in setunion(
      fileset("node", "*.js")
    ) : filename => filemd5("node/${filename}")
  }
}

data "archive_file" "code" {
  type        = "zip"
  source_file = "${path.module}/node/main.js"
  output_path = "${path.module}/.tmp/${random_uuid.lambda_code_hash.result}.zip"
}

resource "aws_lambda_function" "function" {
  function_name = basename(path.module)
  description   = "Copies cloudwatch logs to opensearch"
  filename      = data.archive_file.code.output_path
  role          = aws_iam_role.lambda_assume.arn
  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = "/aws/lambda/${basename(path.module)}"
  }
  handler          = "main.handler"
  runtime          = "nodejs18.x"
  timeout          = 60
  source_code_hash = data.archive_file.code.output_base64sha256
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  for_each      = var.product_log_groups
  statement_id  = "AllowExecutionFromCWLogs_${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function.function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "${each.value}:*"
}
