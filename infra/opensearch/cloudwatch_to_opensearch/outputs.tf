output "cloudwatch_to_opensearch_function_arn" {
  value = aws_lambda_function.function.arn
}

output "cloudwatch_to_opensearch_function_name" {
  value = aws_lambda_function.function.function_name
}
