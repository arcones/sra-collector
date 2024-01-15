module "cloudwatch" {
  source                                = "../cloudwatch"
  cloudwatch_to_opensearch_function_arn = var.cloudwatch_to_opensearch_function_arn
  function_name                         = basename(path.module)
  tags                                  = var.tags
}
