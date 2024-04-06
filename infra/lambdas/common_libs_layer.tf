locals {
  lib_name    = "dependencies"
  deps_folder = "docker"
}

resource "null_resource" "dependencies_watcher" {
  triggers = {
    sha1 = format("%s%s%s",
      filesha1("${path.module}/${local.deps_folder}/db_connection/src/db_connection/db_connection.py"),
      filesha1("${path.module}/${local.deps_folder}/s3_helper/src/s3_helper/s3_helper.py"),
      filesha1("${path.module}/${local.deps_folder}/sqs_helper/src/sqs_helper/sqs_helper.py")
    )
  }
}

resource "aws_s3_object" "common_libs_lambda_layer_zip" {
  bucket = var.s3_code_bucket_id
  source = "${path.module}/${local.lib_name}.zip"
  key    = "${local.lib_name}.zip"
  lifecycle {
    replace_triggered_by = [null_resource.dependencies_watcher]
  }
}

resource "aws_lambda_layer_version" "common_libs_lambda_layer" {
  s3_bucket           = var.s3_code_bucket_id
  s3_key              = aws_s3_object.common_libs_lambda_layer_zip.key
  layer_name          = "${local.lib_name}_layer"
  compatible_runtimes = ["python3.11"]
  lifecycle {
    replace_triggered_by = [null_resource.dependencies_watcher]
  }
}
