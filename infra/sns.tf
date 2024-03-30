resource "aws_sns_topic" "sra_collector_monitoring_topic" {
  name = "sra_collector_monitoring_topic"
}

resource "aws_sns_topic_subscription" "webmaster" {
  topic_arn = aws_sns_topic.sra_collector_monitoring_topic.arn
  protocol  = "email"
  endpoint  = "marta.arcones@gmail.com"
}
