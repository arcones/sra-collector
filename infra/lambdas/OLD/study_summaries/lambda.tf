resource "aws_lambda_function" "study_summaries" {
  function_name    = local.function_name
  description      = "Fetches study summaries for each study ID and sends them to queue"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.lambda_study_summaries.key
  role             = aws_iam_role.study_summaries_lambda_role.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.lambda_study_summaries.output_base64sha256
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.study_ids_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.study_summaries.function_name
  batch_size       = 1
}
