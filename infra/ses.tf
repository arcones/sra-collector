resource "aws_ses_domain_identity" "ses_domain" {
  domain = var.subdomain
}

resource "aws_route53_record" "ses_route53_record" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "_amazonses.${var.subdomain}"
  type    = "TXT"
  ttl     = "600"
  records = [aws_ses_domain_identity.ses_domain.verification_token]
}

resource "aws_ses_email_identity" "webmaster_mail" {
  email = var.webmaster_mail
}

resource "aws_ses_email_identity" "integration_test_mail" {
  email = "arconestech@gmail.com"
}
