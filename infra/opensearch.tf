locals {
  domain_name = "sracollector-opensearch"
}

resource "aws_opensearch_domain" "sracollector_opensearch" {
  domain_name = local.domain_name

  cluster_config {
    instance_type = "t3.small.search"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_logs.arn
    log_type                 = "INDEX_SLOW_LOGS"
  }
  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_logs.arn
    log_type                 = "SEARCH_SLOW_LOGS"
  }
  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_logs.arn
    log_type                 = "ES_APPLICATION_LOGS"
  }

  encrypt_at_rest {
    enabled = true
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }

  tags = var.tags
}

resource "aws_opensearch_domain_policy" "opensearch_access_policy" {
  domain_name = local.domain_name
  access_policies = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          "AWS" = "*"
        }
        Action   = ["es:*", ]
        Resource = "arn:aws:es:${var.aws_region}:${var.aws_account_id}:domain/${local.domain_name}/*"
        Condition : {
          IpAddress : {
            "aws:SourceIp" : ["79.116.183.68/32"]
          }
        },
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "opensearch_logs" {
  name              = "/aws/opensearch/${local.domain_name}"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_cloudwatch_log_resource_policy" "opensearch_cw_logs_policy" {
  policy_name = "${local.domain_name}_logs_policy"
  policy_document = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "es.amazonaws.com"
        }
        Action = [
          "logs:PutLogEvents",
          "logs:PutLogEventsBatch",
          "logs:CreateLogStream",
        ]
        Resource = "arn:aws:logs:*"
      }
    ]
  })
}
