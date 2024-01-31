module "cloudwatch_to_opensearch" {
  source             = "./cloudwatch_to_opensearch"
  domain_arn         = aws_opensearch_domain.sracollector_opensearch.arn
  product_log_groups = var.product_log_groups
}
