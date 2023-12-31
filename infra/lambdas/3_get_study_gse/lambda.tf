resource "aws_lambda_function" "get_study_gse" {
  function_name = local.function_name
  description   = "Fetch GSE for each study ID and send them to queue"
  s3_bucket     = var.s3_bucket_id
  s3_key        = aws_s3_object.get_study_gse_s3_object.key
  role          = aws_iam_role.lambda_assume.arn
  handler       = "${local.function_name}.handler"
  runtime       = "python3.11"
  layers        = [var.common_libs_layer_arn]
  timeout       = 30
  lifecycle {
    replace_triggered_by = [null_resource.code_watcher]
  }
  tags = var.tags
}

resource "null_resource" "code_watcher" {
  triggers = {
    dir_sha1 = sha1(join("", [for file in fileset(local.code_folder, "*") : filesha1("${local.code_folder}/${file}")]))
  }
}


resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.study_ids_sqs_arn
  enabled          = true
  function_name    = aws_lambda_function.get_study_gse.function_name
  batch_size       = 1
}
