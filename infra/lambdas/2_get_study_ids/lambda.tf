resource "aws_lambda_function" "get_study_ids" {
  function_name    = local.function_name
  description      = "Fetch study IDs for the NCBI query and send them to queue"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.get_study_ids_s3_object.key
  role             = aws_iam_role.get_study_ids_lambda_role.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.get_study_ids_code.output_base64sha256
  timeout          = 30
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.user_query_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.get_study_ids.function_name
  batch_size       = 1
}
