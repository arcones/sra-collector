resource "aws_sqs_queue" "A_user_query_queue" {
  name = "A_user_query_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.A_user_query_dlq.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "A_user_query_dlq" {
  name = "A_user_query_dlq"
}

resource "aws_sqs_queue" "B_user_query_pages_queue" {
  name = "B_user_query_pages_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.B_user_query_pages_dlq.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "B_user_query_pages_dlq" {
  name = "B_user_query_pages_dlq"
}

resource "aws_sqs_queue" "C_study_ids_queue" {
  name = "C_study_ids_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.C_study_ids_dlq.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "C_study_ids_dlq" {
  name = "C_study_ids_dlq"
}

resource "aws_sqs_queue" "D_gses_queue" {
  name = "D_gses_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.D_gses_dlq.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "D_gses_dlq" {
  name = "D_gses_dlq"
}

resource "aws_sqs_queue" "E1_srps_queue" {
  name                       = "E1_srps_queue"
  visibility_timeout_seconds = 60 //TODO assess whether to use this config in every queue
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.E1_srps_dlq.arn,
    maxReceiveCount     = 1
  })
}

resource "aws_sqs_queue" "E1_srps_dlq" {
  name = "E1_srps_dlq"
}

resource "aws_sqs_queue" "F_srrs_queue" {
  name = "F_srrs_queue"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.F_srrs_dlq.arn,
    maxReceiveCount     = 1
  })
}

resource "aws_sqs_queue" "F_srrs_dlq" {
  name = "F_srrs_dlq"
}

resource "aws_sqs_queue" "integration_tests_sqs" {
  name = "integration_test_queue"
}
