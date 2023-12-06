resource "aws_sqs_queue" "study_ids_queue" {
  name                        = "study_ids_queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  deduplication_scope         = "messageGroup"
}

resource "aws_sqs_queue" "pending_srp_queue" {
  name                        = "pending_srp_queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  deduplication_scope         = "messageGroup"
}

resource "aws_sqs_queue" "study_summaries_queue" {
  name                        = "study_summaries_queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  deduplication_scope         = "messageGroup"
}
