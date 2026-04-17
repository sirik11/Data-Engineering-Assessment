# S3 buckets are pre-provisioned — referenced by constructed name and ARN
# Bucket names use hyphens (S3 requirement); candidate name uses underscores (IAM requirement)
locals {
  input_bucket_name  = replace("${local.app_name}-input-bucket", "_", "-")
  output_bucket_name = replace("${local.app_name}-output-bucket", "_", "-")
  input_bucket_arn   = "arn:aws:s3:::${replace("${local.app_name}-input-bucket", "_", "-")}"
  output_bucket_arn  = "arn:aws:s3:::${replace("${local.app_name}-output-bucket", "_", "-")}"
}

module "ecr_repo" {
  source       = "../modules/ecr-repo"
  repo_name    = "${local.app_name}-ecr"
  default_tags = local.default_tags
}

module "lambda_function" {
  source                = "../modules/lambda"
  lambda_name           = "${local.app_name}-file-processor"
  role_name             = "${local.app_name}-file-processor-role"
  log_retention_in_days = 14
  image_uri             = "${module.ecr_repo.repository_url}:latest"
  timeout               = 15
  memory_size           = 256
  environment_variables = {
    OUTPUT_BUCKET = local.output_bucket_name
  }
  default_tags = local.default_tags
}

# IAM policy: least privilege — Lambda can only read input and write output
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "${local.app_name}-lambda-s3-policy"
  role = module.lambda_function.role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${local.input_bucket_arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = local.input_bucket_arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${local.output_bucket_arn}/*"
      },
    ]
  })
}

# IAM policy for the deployment user to configure S3 notifications and upload test files
resource "aws_iam_user_policy" "user_s3_policy" {
  name = "${local.app_name}-user-s3-policy"
  user = var.candidate_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutBucketNotification", "s3:GetBucketNotification"]
        Resource = local.input_bucket_arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = ["${local.input_bucket_arn}/*", "${local.output_bucket_arn}/*"]
      }
    ]
  })
}

# Allow S3 to invoke the Lambda function
resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function.lambda_arn
  principal     = "s3.amazonaws.com"
  source_arn    = local.input_bucket_arn
}

# Trigger Lambda on any CSV upload to the input bucket
resource "aws_s3_bucket_notification" "s3_notification" {
  bucket = local.input_bucket_name
  lambda_function {
    lambda_function_arn = module.lambda_function.lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }
  depends_on = [aws_lambda_permission.allow_bucket]
}
