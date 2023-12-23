resource "aws_iam_role" "lambda_assume" {
  name = "${local.function_name}_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action = ["sts:AssumeRole", ],
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

resource "aws_iam_role_policy" "input_sqs_policy" {
  name = "input_sqs_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Version = "2008-10-17"
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
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["sqs:sendmessage"]
        Effect   = "Allow"
        Resource = var.user_query_pages_sqs_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "ssm_policy" {
  name = "ssm_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["ssm:GetParameter"]
        Effect   = "Allow"
        Resource = var.log_level_parameter_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "secret_policy" {
  name = "secret_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["secretsmanager:GetSecretValue"]
        Effect   = "Allow"
        Resource = "arn:aws:secretsmanager:eu-central-1:120715685161:secret:rds!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6-bNjnDK"
      },
    ]
  })
}

resource "aws_iam_role_policy" "kms_policy" {
  name = "kms_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["kms:*"]
        Effect   = "Allow"
        Resource = "arn:aws:kms:eu-central-1:120715685161:key/33d5669b-6a9e-4055-be8c-8231920dd860"
      },
    ]
  })
}
