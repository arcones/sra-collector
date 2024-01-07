resource "aws_lambda_function" "cloudwatch_to_opensearch" {
  function_name = local.function_name
  description   = "Copies cloudwatch logs to opensearch"
  s3_bucket     = var.s3_bucket_id
  s3_key        = aws_s3_object.cloudwatch_to_opensearch_s3_object.key
  role          = aws_iam_role.lambda_assume.arn
  handler       = "${local.function_name}.handler"
  runtime       = "nodejs18.x"
  timeout       = 300
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

resource "aws_lambda_permission" "allow_cloudwatch" {
  for_each      = var.product_log_groups
  statement_id  = "AllowExecutionFromCWLogs_${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cloudwatch_to_opensearch.function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "${each.value}:*"
}
