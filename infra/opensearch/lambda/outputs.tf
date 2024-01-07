output "cloudwatch_to_opensearch_function_arn" {
  value = aws_lambda_function.cloudwatch_to_opensearch.arn
}

output "cloudwatch_to_opensearch_function_name" {
  value = aws_lambda_function.cloudwatch_to_opensearch.function_name
}
