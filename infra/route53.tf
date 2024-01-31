locals {
  subdomain = "martaarcones.net"
}

resource "aws_acm_certificate" "certificate" {
  domain_name       = "sra-collector.${local.subdomain}"
  validation_method = "DNS"
}

data "aws_route53_zone" "zone" {
  name         = local.subdomain
  private_zone = false
}

resource "aws_route53_record" "records" {
  for_each = {
    for dvo in aws_acm_certificate.certificate.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.zone.zone_id
}

resource "aws_acm_certificate_validation" "certificate_validation" {
  certificate_arn         = aws_acm_certificate.certificate.arn
  validation_record_fqdns = [for record in aws_route53_record.records : record.fqdn]
}

resource "aws_apigatewayv2_domain_name" "apigateway_domain_name" {
  domain_name = "sra-collector.${local.subdomain}"

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.certificate.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  depends_on = [aws_acm_certificate_validation.certificate_validation]
}

resource "aws_route53_record" "record" {
  name    = aws_apigatewayv2_domain_name.apigateway_domain_name.domain_name
  type    = "A"
  zone_id = data.aws_route53_zone.zone.zone_id

  alias {
    name                   = aws_apigatewayv2_domain_name.apigateway_domain_name.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.apigateway_domain_name.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
