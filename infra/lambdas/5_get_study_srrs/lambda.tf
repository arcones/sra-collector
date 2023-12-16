resource "aws_lambda_function" "get_study_srrs" {
  function_name    = local.function_name
  description      = "Fetch SRRs for a given study"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.get_study_srrs_s3_object.key
  role             = aws_iam_role.lambda_assume.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.get_study_srrs_code.output_base64sha256
  layers           = [var.pysradb_layer_arn]
  timeout          = 10
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.srps_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.get_study_srrs.function_name
  batch_size       = 1
}
