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

resource "aws_iam_role" "user_query_lambda_role" {
  name               = "user_query_lambda_role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}


resource "aws_iam_role_policy_attachment" "user_query_lambda_policy" {
  role       = aws_iam_role.user_query_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
