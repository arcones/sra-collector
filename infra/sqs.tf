resource "aws_sqs_queue" "study_ids_queue" {
  name = "study_ids_queue"
}

resource "aws_sqs_queue" "study_summaries_queue" {
  name = "study_summaries_queue"
}
