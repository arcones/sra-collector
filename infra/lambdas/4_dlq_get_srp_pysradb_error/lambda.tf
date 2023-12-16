resource "aws_lambda_function" "dlq_get_srp_pysradb_error" {
  function_name    = local.function_name
  description      = "Fetch SRPs for a given study"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.dlq_get_srp_pysradb_error_s3_object.key
  role             = aws_iam_role.lambda_assume.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.dlq_get_srp_pysradb_error_code.output_base64sha256
  layers           = [aws_lambda_layer_version.pysradb_lambda_layer.arn]
  timeout          = 10
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.gses_dlq_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.dlq_get_srp_pysradb_error.function_name
  batch_size       = 1
}
