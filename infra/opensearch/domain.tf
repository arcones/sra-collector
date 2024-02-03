locals {
  domain_name = "sracollector-opensearch"
}

resource "aws_opensearch_domain" "sracollector_opensearch" {
  domain_name = local.domain_name

  cluster_config {
    instance_type = "t3.small.search"
  }

  encrypt_at_rest {
    enabled = true
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }
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
        Resource = "${aws_opensearch_domain.sracollector_opensearch.arn}/*"
        Condition : {
          IpAddress : {
            "aws:SourceIp" : [
              "86.127.230.245/32",
              "79.116.183.0/24"
            ]
          }
        },
      }
    ]
  })
}
