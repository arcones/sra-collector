resource "aws_s3_object" "pysradb_lambda_layer_zip" {
  bucket = var.s3_bucket_id
  source = "${path.module}/pysradb.zip"
  key    = "pysradb.zip"
}

resource "aws_lambda_layer_version" "pysradb_lambda_layer" {
  s3_bucket           = var.s3_bucket_id
  s3_key              = aws_s3_object.pysradb_lambda_layer_zip.key
  layer_name          = "pysradb_layer"
  compatible_runtimes = ["python3.11"]
}
