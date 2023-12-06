data "archive_file" "lambda_user_query" {
  type = "zip"

  source_file = "${path.module}/python3/${local.function_name}.py"
  output_path = "${path.module}/${local.function_name}.zip"
}


resource "aws_s3_object" "lambda_user_query" {
  bucket = var.s3_bucket_id

  key    = "${local.function_name}.zip"
  source = data.archive_file.lambda_user_query.output_path

  etag = filemd5(data.archive_file.lambda_user_query.output_path)
}
