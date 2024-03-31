resource "aws_sqs_queue" "A_user_query" {
  name                       = "A_user_query"
  visibility_timeout_seconds = 40
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.A_to_B_DLQ.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "A_to_B_DLQ" {
  name = "A_to_B_DLQ"
}

resource "aws_sqs_queue" "B_query_pages" {
  name                       = "B_query_pages"
  visibility_timeout_seconds = 40
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.B_to_C_DLQ.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "B_to_C_DLQ" {
  name = "B_to_C_DLQ"
}

resource "aws_sqs_queue" "C_study_ids" {
  name                       = "C_study_ids"
  visibility_timeout_seconds = 40
  delay_seconds              = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.C_to_D_DLQ.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "C_to_D_DLQ" {
  name = "C_to_D_DLQ"
}

resource "aws_sqs_queue" "D_geos" {
  name                       = "D_geos"
  visibility_timeout_seconds = 40
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.D_to_E_DLQ.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "D_to_E_DLQ" {
  name = "D_to_E_DLQ"
}

resource "aws_sqs_queue" "E_srps" {
  name                       = "E_srps"
  visibility_timeout_seconds = 40
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.E_to_F_DLQ.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "E_to_F_DLQ" {
  name = "E_to_F_DLQ"
}

resource "aws_sqs_queue" "F_srrs" {
  name                       = "F_srrs"
  visibility_timeout_seconds = 40
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.F_to_G_DLQ.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "F_to_G_DLQ" {
  name = "F_to_G_DLQ"
}

resource "aws_sqs_queue" "G_srr_metadata" {
  name                       = "G_srr_metadata"
  visibility_timeout_seconds = 40
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.G_to_S3_DLQ.arn,
    maxReceiveCount     = 2
  })
}

resource "aws_sqs_queue" "G_to_S3_DLQ" {
  name = "G_to_S3_DLQ"
}

resource "aws_sqs_queue" "H_user_feedback" {
  name                       = "H_user_feedback"
  visibility_timeout_seconds = 40
}


resource "aws_sqs_queue" "integration_tests_sqs" {
  name = "integration_test_queue"
}
