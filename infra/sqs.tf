resource "aws_sqs_queue" "A_user_query" {
  name = "A_user_query"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.A_DLQ_user_query_2_query_pages.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "A_DLQ_user_query_2_query_pages" {
  name = "A_DLQ_user_query_2_query_pages"
}

resource "aws_sqs_queue" "B_query_pages" {
  name = "B_query_pages"
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.B_DLQ_query_pages_2_study_ids.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "B_DLQ_query_pages_2_study_ids" {
  name = "B_DLQ_query_pages_2_study_ids"
}

resource "aws_sqs_queue" "C_study_ids" {
  name                       = "C_study_ids"
  visibility_timeout_seconds = 120
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.C_DLQ_study_ids_2_gses.arn,
    maxReceiveCount     = 10
  })
}

resource "aws_sqs_queue" "C_DLQ_study_ids_2_gses" {
  name = "C_DLQ_study_ids_2_gses"
}

resource "aws_sqs_queue" "D_gses" {
  name                       = "D_gses"
  visibility_timeout_seconds = 150
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.D_DLQ_gses_2_srps.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "D_DLQ_gses_2_srps" {
  name = "D_DLQ_gses_2_srps"
}

resource "aws_sqs_queue" "E_srps" {
  name                       = "E_srps"
  visibility_timeout_seconds = 360
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.E_DLQ_srps_2_srrs.arn,
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "E_DLQ_srps_2_srrs" {
  name = "E_DLQ_srps_2_srrs"
}

resource "aws_sqs_queue" "F_srrs" {
  name = "F_srrs"
}

resource "aws_sqs_queue" "integration_tests_sqs" {
  name = "integration_test_queue"
}
