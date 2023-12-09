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

resource "aws_iam_role" "get_study_ids_lambda_role" {
  name               = "get_study_ids_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_role_policy_attachment" "get_study_ids_lambda_basic_policy" {
  role       = aws_iam_role.get_study_ids_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "input_sqs_policy" {
  name = "input_sqs_policy"
  role = aws_iam_role.get_study_ids_lambda_role.name
  policy = jsonencode({
    Statement = [
      {
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Effect   = "Allow"
        Resource = var.user_query_sqs_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "output_sqs_policy" {
  name = "output_sqs_policy"
  role = aws_iam_role.get_study_ids_lambda_role.name
  policy = jsonencode({
    Statement = [
      {
        Action = [
          "sqs:sendmessage",
        ]
        Effect   = "Allow"
        Resource = var.study_ids_sqs_arn
      },
    ]
  })
}
