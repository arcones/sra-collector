output "paginate_user_query_function_name" {
  value = aws_lambda_function.get_user_query.function_name
}

output "paginate_user_query_invoke_arn" {
  value = aws_lambda_function.get_user_query.invoke_arn
}
