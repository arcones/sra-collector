locals {
  lib_name = "dependencies"
}

resource "aws_s3_object" "common_libs_lambda_layer_zip" {
  bucket = var.s3_bucket_id
  source = "${path.module}/${local.lib_name}.zip"
  key    = "${local.lib_name}.zip"
  etag   = filemd5("${path.module}/${local.lib_name}.zip")
}

resource "aws_lambda_layer_version" "common_libs_lambda_layer" {
  s3_bucket           = var.s3_bucket_id
  s3_key              = aws_s3_object.common_libs_lambda_layer_zip.key
  layer_name          = "${local.lib_name}_layer"
  compatible_runtimes = ["python3.11"]
  source_code_hash    = filebase64sha256(aws_s3_object.common_libs_lambda_layer_zip.source)
}
