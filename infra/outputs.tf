output "sra_collector_custom_domain" {
  value = "https://${aws_apigatewayv2_api_mapping.api.domain_name}"
}
