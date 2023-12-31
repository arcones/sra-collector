resource "aws_sns_topic" "admin" {
  name = "sra_collector_admin_topic"
  tags = var.tags
}

resource "aws_sns_topic_subscription" "admin_mail" {
  topic_arn = aws_sns_topic.admin.arn
  protocol  = "email"
  endpoint  = "marta.arcones@gmail.com"
}
