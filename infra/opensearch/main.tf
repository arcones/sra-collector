module "lambda" {
  source             = "./lambda"
  s3_bucket_id       = var.s3_bucket_id
  domain_arn         = aws_opensearch_domain.sracollector_opensearch.arn
  product_log_groups = var.product_log_groups
  tags               = var.tags
}
