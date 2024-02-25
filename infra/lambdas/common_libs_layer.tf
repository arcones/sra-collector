locals {
  lib_name    = "dependencies"
  deps_folder = "docker"
}

resource "null_resource" "dependencies_watcher" {
  triggers = {
    sha1 = filesha1("${path.module}/${local.deps_folder}/postgres_connection/src/postgres_connection/postgres_connection.py")
  }
}

resource "aws_s3_object" "common_libs_lambda_layer_zip" {
  bucket = var.s3_bucket_id
  source = "${path.module}/${local.lib_name}.zip"
  key    = "${local.lib_name}.zip"
  lifecycle {
    replace_triggered_by = [null_resource.dependencies_watcher]
  }
}

resource "aws_lambda_layer_version" "common_libs_lambda_layer" {
  s3_bucket           = var.s3_bucket_id
  s3_key              = aws_s3_object.common_libs_lambda_layer_zip.key
  layer_name          = "${local.lib_name}_layer"
  compatible_runtimes = ["python3.11"]
  lifecycle {
    replace_triggered_by = [null_resource.dependencies_watcher]
  }
}
