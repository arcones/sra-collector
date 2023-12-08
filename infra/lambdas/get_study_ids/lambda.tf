resource "aws_lambda_function" "get_study_ids" {
  function_name    = local.function_name
  description      = "Fetches study IDs for the query and send them to queue"
  s3_bucket        = var.s3_bucket_id
  s3_key           = aws_s3_object.lambda_get_study_ids.key
  role             = aws_iam_role.get_study_ids_lambda_role.arn
  handler          = "${local.function_name}.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.lambda_get_study_ids.output_base64sha256
  timeout          = 500
}
