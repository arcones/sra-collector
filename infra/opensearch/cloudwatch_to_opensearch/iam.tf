resource "aws_iam_role" "lambda_assume" {
  name = "${basename(path.module)}_role"
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
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_policy" {
  role       = aws_iam_role.lambda_assume.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "cloudwatch_to_opensearch_policy" {
  name = "cloudwatch_to_opensearch_policy"
  role = aws_iam_role.lambda_assume.name
  policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Action   = ["es:*", ],
        Effect   = "Allow",
        Resource = "${var.domain_arn}/*"
      }
    ]
  })
}
