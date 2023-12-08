data "archive_file" "lambda_get_study_ids" {
  type = "zip"

  source_file = "${path.module}/python3/${local.function_name}.py"
  output_path = "${path.module}/${local.function_name}.zip"
}

resource "aws_s3_object" "lambda_get_study_ids" {
  bucket = var.s3_bucket_id

  key    = "${local.function_name}.zip"
  source = data.archive_file.lambda_get_study_ids.output_path

  etag = filemd5(data.archive_file.lambda_get_study_ids.output_path)
}
