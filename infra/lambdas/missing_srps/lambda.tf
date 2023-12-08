resource "aws_lambda_function" "missing_srps" {
  function_name    = local.function_name
  description      = "Alternative method to fetch SRPs for a given study"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.lambda_missing_srps.key
  role             = aws_iam_role.missing_srps_lambda_role.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.lambda_missing_srps.output_base64sha256
  layers           = [aws_lambda_layer_version.missing_srps_lambda_layer.arn]
  timeout          = 10
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.pending_srp_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.missing_srps.function_name
  batch_size       = 1
}
