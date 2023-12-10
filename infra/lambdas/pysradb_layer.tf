#locals {
#  layer_input_folder    = "${path.module}/bundle"
#  layer_name            = "pysradb_lambda_layer"
#  layer_output_zip_path = "${local.layer_name}.zip"
#  requirements_path     = "${path.module}/pysradb-requirements.txt"
#}
#
#resource "null_resource" "lambda_missing_srps_layer_bundle_creator" {
#  triggers = {
#    requirements = timestamp()
#  }
#  provisioner "local-exec" {
#    command = <<EOT
#        rm -rf ${local.layer_input_folder}
#        mkdir -p ${local.layer_input_folder}/python
#
#        pip install -r ${local.requirements_path} -t ${local.layer_input_folder}/python
#    EOT
#  }
#}
#
#data "archive_file" "lambda_missing_srps_layer" {
#  type        = "zip"
#  source_dir  = local.layer_input_folder
#  output_path = local.layer_output_zip_path
#  depends_on  = [null_resource.lambda_missing_srps_layer_bundle_creator]
#}
#
#resource "aws_s3_object" "lambda_layer_zip" {
#  bucket = var.s3_bucket_id
#  key    = local.layer_output_zip_path
#  source = local.layer_output_zip_path
#}
#
#resource "aws_lambda_layer_version" "missing_srps_lambda_layer" {
#  s3_bucket           = var.s3_bucket_id
#  s3_key              = aws_s3_object.lambda_layer_zip.key
#  layer_name          = local.layer_name
#  compatible_runtimes = ["python3.11"]
#}
