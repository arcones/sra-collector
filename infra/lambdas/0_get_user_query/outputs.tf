output "get_user_query_invoke_arn" {
  value = aws_lambda_function.get_user_query.invoke_arn
}

output "get_user_query_function_name" {
  value = aws_lambda_function.get_user_query.function_name
}
