module "lambda" {
  source                  = "../lambda"
  code_path               = path.module
  common_libs_layer_arn   = var.common_libs_layer_arn
  function_name           = basename(path.module)
  log_level_parameter_arn = var.log_level_parameter_arn
  input_sqs_arn           = var.srps_sqs_arn
  output_sqs_arn          = var.srrs_sqs_arn
  rds_kms_key_arn         = var.rds_kms_key_arn
  rds_secret_arn          = var.rds_secret_arn
  tags                    = var.tags
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = var.srps_sqs_arn
  enabled          = true
  function_name    = module.lambda.function.function_name
  batch_size       = 1
}
