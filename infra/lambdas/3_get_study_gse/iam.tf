resource "aws_iam_role" "lambda_assume" {
  name = "get_study_gse_lambda_role"
  assume_role_policy = jsonencode({
    Statement = [
      {
        Action = ["sts:AssumeRole"],
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_policy" {
  role       = aws_iam_role.lambda_assume.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "secret_policy" {
  name = "secret_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Statement = [
      {
        Action   = ["secretsmanager:GetSecretValue"]
        Effect   = "Allow"
        Resource = var.ncbi_api_key_secret_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "input_sqs_policy" {
  name = "input_sqs_policy"
  role = aws_iam_role.lambda_assume.name
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

resource "aws_iam_role_policy" "output_sqs_policy" {
  name = "output_sqs_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Statement = [
      {
        Action   = ["sqs:sendmessage"]
        Effect   = "Allow"
        Resource = [var.gses_sqs_arn]
      },
    ]
  })
}

resource "aws_iam_role_policy" "ssm_policy" {
  name = "ssm_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Statement = [
      {
        Action   = ["ssm:GetParameter"]
        Effect   = "Allow"
        Resource = var.log_level_parameter_arn
      },
    ]
  })
}
