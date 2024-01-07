data "archive_file" "cloudwatch_to_opensearch_code" {
  type        = "zip"
  source_file = "${path.module}/${local.code_folder}/${local.function_name}.js"
  output_path = "${path.module}/${local.function_name}.zip"
}

resource "aws_s3_object" "cloudwatch_to_opensearch_s3_object" {
  bucket = var.s3_bucket_id
  key    = "${local.function_name}.zip"
  source = data.archive_file.cloudwatch_to_opensearch_code.output_path
  etag   = filemd5(data.archive_file.cloudwatch_to_opensearch_code.output_path)
  tags   = var.tags
}
