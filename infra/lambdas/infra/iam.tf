resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2008-10-17"
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
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "input_sqs_policy" {
  count = var.queues.input_sqs_arn == null ? 0 : 1
  name  = "input_sqs_policy"
  role  = aws_iam_role.lambda_role.name
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
        Resource = var.queues.input_sqs_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "output_sqs_policy" {
  count = length(var.queues.output_sqs_arns)
  name  = "output_sqs_policy_${count.index}"
  role  = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["sqs:sendmessage"]
        Effect   = "Allow"
        Resource = var.queues.output_sqs_arns[count.index]
      },
    ]
  })
}

resource "aws_iam_role_policy" "dlq_sqs_policy" {
  count = var.queues.dlq_arn == null ? 0 : 1
  name  = "dlq_sqs_policy"
  role  = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["sqs:sendmessage"]
        Effect   = "Allow"
        Resource = var.queues.dlq_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "rds_secret_policy" {
  count = var.rds_secret_arn == null ? 0 : 1
  name  = "rds_secret_policy"
  role  = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["secretsmanager:GetSecretValue"]
        Effect   = "Allow"
        Resource = var.rds_secret_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "ncbi_secret_policy" {
  count = var.ncbi_secret_arn == null ? 0 : 1
  name  = "ncbi_secret_policy"
  role  = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["secretsmanager:GetSecretValue"]
        Effect   = "Allow"
        Resource = var.ncbi_secret_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "kms_policy" {
  count = var.rds_kms_key_arn == null ? 0 : 1
  name  = "kms_policy"
  role  = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["kms:decrypt"]
        Effect   = "Allow"
        Resource = var.rds_kms_key_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "s3_policy" {
  count = var.s3_reports_bucket_arn == null ? 0 : 1
  name  = "s3_policy"
  role  = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["s3:PutObject", "s3:GetObject", "s3:HeadObject"]
        Effect   = "Allow"
        Resource = "${var.s3_reports_bucket_arn}/*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "ses_policy" {
  count = var.webmaster_mail == null ? 0 : 1
  name  = "ses_policy"
  role  = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["ses:SendRawEmail"]
        Effect   = "Allow"
        Resource = "*"
      },
    ]
  })
}
