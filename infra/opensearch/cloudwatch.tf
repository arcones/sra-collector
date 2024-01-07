#resource "aws_cloudwatch_log_group" "opensearch_logs" {
#  name              = "/aws/opensearch/${local.domain_name}"
#  retention_in_days = 7
#  tags              = var.tags
#}
