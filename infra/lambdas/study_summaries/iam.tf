data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "study_summaries_lambda_role" {
  name               = "study_summaries_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}


resource "aws_iam_role_policy_attachment" "study_summaries_lambda_basic_policy" {
  role       = aws_iam_role.study_summaries_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "aws_iam_role_policy" "study_summaries_sqs_policy" {
  name = "study_summaries_lambda_sqs"
  role = aws_iam_role.study_summaries_lambda_role.name
  policy = jsonencode({
    Statement = [
      {
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Effect   = "Allow"
        Resource = var.study_ids_sqs_arn
      },
    ]
  })
}
