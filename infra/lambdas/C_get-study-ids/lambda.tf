resource "random_uuid" "lambda_code_hash" {
  keepers = {
    for filename in setunion(
      fileset("python3", "*.py")
    ) : filename => filemd5("python3/${filename}")
  }
}

data "archive_file" "code" {
  type        = "zip"
  source_file = "${path.module}/python3/main.py"
  output_path = "${path.module}/.tmp/${random_uuid.lambda_code_hash.result}.zip"
}

resource "aws_lambda_function" "function" {
  function_name    = basename(path.module)
  description      = "Fetch study IDs for the NCBI query and send them to queue"
  filename         = data.archive_file.code.output_path
  role             = aws_iam_role.lambda_assume.arn
  handler          = "main.handler"
  runtime          = "python3.11"
  layers           = [var.common_libs_layer_arn]
  timeout          = 30
  source_code_hash = data.archive_file.code.output_base64sha256
  tags             = var.tags
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.user_query_pages_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.function.function_name
  batch_size       = 1
}
