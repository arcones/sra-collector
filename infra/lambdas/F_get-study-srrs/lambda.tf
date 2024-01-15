module "lambda" {
  source                = "../lambda"
  code_path             = path.module
  common_libs_layer_arn = var.common_libs_layer_arn
  function_name         = basename(path.module)
  role_arn              = aws_iam_role.lambda_assume.arn
  tags                  = var.tags
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.srps_sqs_arn
  enabled          = true
  function_name    = module.lambda.function.function_name
  batch_size       = 1
}
