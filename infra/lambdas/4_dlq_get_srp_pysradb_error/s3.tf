data "archive_file" "dlq_get_srp_pysradb_error_code" {
  type        = "zip"
  source_file = "${path.module}/${local.code_folder}/${local.function_name}.py"
  output_path = "${path.module}/${local.function_name}.zip"
}

resource "aws_s3_object" "dlq_get_srp_pysradb_error_s3_object" {
  bucket = var.s3_bucket_id
  key    = "${local.function_name}.zip"
  source = data.archive_file.dlq_get_srp_pysradb_error_code.output_path
  etag   = filemd5(data.archive_file.dlq_get_srp_pysradb_error_code.output_path)
}
