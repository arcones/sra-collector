resource "aws_lambda_function" "get_study_gse" {
  function_name    = local.function_name
  description      = "Fetch GSE for each study ID and send them to queue"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.get_study_gse_s3_object.key
  role             = aws_iam_role.lambda_assume.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.get_study_gse_code.output_base64sha256
  timeout          = 30
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.study_ids_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.get_study_gse.function_name
  batch_size       = 1
}
