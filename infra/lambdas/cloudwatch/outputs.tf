output "cloudwatch_log_group_arn" {
  value = aws_cloudwatch_log_group.lambda_logs.arn
}
