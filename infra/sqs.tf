resource "aws_sqs_queue" "study_ids_queue" {
  name = "study_ids_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.study_ids_dlq.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "study_ids_dlq" {
  name = "study_ids_dlq"
}

resource "aws_sqs_queue" "pending_srp_queue" {
  name = "pending_srp_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.pending_srp_dlq.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "pending_srp_dlq" {
  name = "pending_srp_dlq"
}

resource "aws_sqs_queue" "study_summaries_queue" {
  name = "study_summaries_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.study_summaries_dlq.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "study_summaries_dlq" {
  name = "study_summaries_dlq"
}
