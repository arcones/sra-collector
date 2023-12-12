locals {
  layer_input_folder    = "${path.module}/bundle"
  layer_name            = "pysradb_lambda_layer"
  layer_output_zip_path = "${local.layer_name}.zip"
  requirements_path     = "${path.module}/requirements.txt"
  runtime               = "python3.11"
}

resource "null_resource" "pysradb_lambda_layer_bundle_creator" {
  triggers = {
    requirements = timestamp()
  }
  provisioner "local-exec" {
    command = <<EOT
        rm -rf ${local.layer_input_folder}
        mkdir -p ${local.layer_input_folder}/python

        rm -rf ${path.module}/env_${local.layer_name}

        virtualenv -p ${local.runtime} ${path.module}/env_${local.layer_name}
        source ${path.module}/env_${local.layer_name}/bin/activate

        pip install -r ${local.requirements_path} -t ${local.layer_input_folder}/python
    EOT
  }
}

data "archive_file" "pysradb_lambda_layer" {
  type        = "zip"
  source_dir  = local.layer_input_folder
  output_path = local.layer_output_zip_path
  depends_on  = [null_resource.pysradb_lambda_layer_bundle_creator]
}

resource "aws_s3_object" "pysradb_lambda_layer_zip" {
  bucket = var.s3_bucket_id
  key    = local.layer_output_zip_path
  source = local.layer_output_zip_path
  depends_on = [
    null_resource.pysradb_lambda_layer_bundle_creator,
    data.archive_file.pysradb_lambda_layer
  ]
}

resource "aws_lambda_layer_version" "pysradb_lambda_layer" {
  s3_bucket           = var.s3_bucket_id
  s3_key              = aws_s3_object.pysradb_lambda_layer_zip.key
  layer_name          = local.layer_name
  compatible_runtimes = [local.runtime]
}
