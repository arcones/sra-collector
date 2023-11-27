output "user_query_function_name" {
  value = aws_lambda_function.user_query.function_name
}

output "user_query_invoke_arn" {
  value = aws_lambda_function.user_query.invoke_arn
}
