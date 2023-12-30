resource "aws_sqs_queue" "user_query_queue" {
  name = "user_query_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.user_query_dlq.arn,
    maxReceiveCount     = 3
  })
  tags = var.tags
}

resource "aws_sqs_queue" "user_query_dlq" {
  name = "user_query_dlq"
}

resource "aws_sqs_queue" "user_query_pages_queue" {
  name = "user_query_pages_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.user_query_pages_dlq.arn,
    maxReceiveCount     = 3
  })
  tags = var.tags
}

resource "aws_sqs_queue" "user_query_pages_dlq" {
  name = "user_query_pages_dlq"
  tags = var.tags
}

resource "aws_sqs_queue" "study_ids_queue" {
  name = "study_ids_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.study_ids_dlq.arn,
    maxReceiveCount     = 3
  })
  tags = var.tags
}

resource "aws_sqs_queue" "study_ids_dlq" {
  name = "study_ids_dlq"
  tags = var.tags
}

resource "aws_sqs_queue" "gses_queue" {
  name = "gses_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.gses_dlq.arn,
    maxReceiveCount     = 3
  })
  tags = var.tags
}

resource "aws_sqs_queue" "gses_dlq" {
  name = "gses_dlq"
  tags = var.tags
}

resource "aws_sqs_queue" "srps_queue" {
  name = "srps_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.srps_dlq.arn,
    maxReceiveCount     = 3
  })
  tags = var.tags
}

resource "aws_sqs_queue" "srps_dlq" {
  name = "srps_dlq"
  tags = var.tags
}

resource "aws_sqs_queue" "srrs_queue" {
  name = "srrs_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.srrs_dlq.arn,
    maxReceiveCount     = 3
  })
  tags = var.tags
}

resource "aws_sqs_queue" "srrs_dlq" {
  name = "srrs_dlq"
  tags = var.tags
}
