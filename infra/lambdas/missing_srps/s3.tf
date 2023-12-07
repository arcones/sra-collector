data "archive_file" "lambda_missing_srps" {
  type = "zip"

  source_file = "${path.module}/python3/${local.function_name}.py"
  output_path = "${path.module}/${local.function_name}.zip"
}


resource "aws_s3_object" "lambda_missing_srps" {
  bucket = var.s3_bucket_id

  key    = "${local.function_name}.zip"
  source = data.archive_file.lambda_missing_srps.output_path

  etag = filemd5(data.archive_file.lambda_missing_srps.output_path)
}
