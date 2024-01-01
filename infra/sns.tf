resource "aws_sns_topic" "admin" {
  name = "sra_collector_admin_topic"
  tags = var.tags
}

module "notify_slack" {
  source         = "terraform-aws-modules/notify-slack/aws"
  version        = "6.1.0"
  sns_topic_name = aws_sns_topic.admin.name

  slack_webhook_url = "https://hooks.slack.com/services/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"
  slack_channel     = "sra-collector-alerts"
  slack_username    = "AWS WatchDog"
  slack_emoji       = ":rotating_light:"
  tags              = var.tags
}
