locals {
  lib_name = "pysradb"
}

resource "aws_s3_object" "pysradb_lambda_layer_zip" {
  bucket = var.s3_bucket_id
  source = "${path.module}/${local.lib_name}.zip"
  key    = "${local.lib_name}.zip"
}

resource "aws_lambda_layer_version" "pysradb_lambda_layer" {
  s3_bucket           = var.s3_bucket_id
  s3_key              = aws_s3_object.pysradb_lambda_layer_zip.key
  layer_name          = "${local.lib_name}_layer"
  compatible_runtimes = ["python3.11"]
}
