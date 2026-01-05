# =============================================================================
# Lambda Function for SGA PostgreSQL Schema Migration
# =============================================================================
# Lambda function that applies schema changes to Aurora PostgreSQL.
# Runs inside VPC to access RDS Proxy, invoked by GitHub Actions workflow.
#
# Architecture:
# GitHub Actions -> Lambda (this) -> RDS Proxy -> Aurora PostgreSQL
#
# Operations:
# - apply: Apply schema files from S3
# - verify: Verify schema state
#
# Security:
# - VPC-attached (private subnets)
# - IAM auth to RDS Proxy
# - S3 read access for schema files
# =============================================================================

# =============================================================================
# IAM Role for Lambda
# =============================================================================

resource "aws_iam_role" "sga_schema_migrator" {
  name = "${local.name_prefix}-sga-schema-migrator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${local.name_prefix}-sga-schema-migrator-role"
    Module      = "SGA"
    Feature     = "Schema Migration"
    Description = "IAM role for PostgreSQL schema migrator Lambda"
  }
}

# VPC access policy
resource "aws_iam_role_policy_attachment" "sga_schema_migrator_vpc" {
  role       = aws_iam_role.sga_schema_migrator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# RDS and Secrets Manager access policy
resource "aws_iam_role_policy" "sga_schema_migrator_rds" {
  name = "${local.name_prefix}-sga-schema-migrator-rds"
  role = aws_iam_role.sga_schema_migrator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRDSConnect"
        Effect = "Allow"
        Action = "rds-db:connect"
        Resource = "arn:aws:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser:${aws_db_proxy.sga.id}/*"
      },
      {
        Sid    = "AllowSecretsAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.sga_rds_master.arn
      },
      {
        Sid    = "AllowKMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = aws_kms_key.sga_rds.arn
      }
    ]
  })
}

# S3 access policy for schema files
resource "aws_iam_role_policy" "sga_schema_migrator_s3" {
  name = "${local.name_prefix}-sga-schema-migrator-s3"
  role = aws_iam_role.sga_schema_migrator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSchemaRead"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.sga_documents.arn,
          "${aws_s3_bucket.sga_documents.arn}/schema/*"
        ]
      }
    ]
  })
}

# CloudWatch Logs policy
resource "aws_iam_role_policy" "sga_schema_migrator_logs" {
  name = "${local.name_prefix}-sga-schema-migrator-logs"
  role = aws_iam_role.sga_schema_migrator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}-sga-schema-migrator:*"
    }]
  })
}

# =============================================================================
# Lambda Function
# =============================================================================

# Placeholder for deployment package
# Actual code will be deployed via GitHub Actions
data "archive_file" "sga_schema_migrator_placeholder" {
  type        = "zip"
  output_path = "${path.module}/sga_schema_migrator_placeholder.zip"

  source {
    content  = <<EOF
# Placeholder - actual code deployed via GitHub Actions
def handler(event, context):
    return {"error": "Placeholder - deploy actual code via GitHub Actions"}
EOF
    filename = "schema_migrator.py"
  }
}

resource "aws_lambda_function" "sga_schema_migrator" {
  function_name = "${local.name_prefix}-sga-schema-migrator"
  description   = "PostgreSQL schema migrator for SGA inventory"
  role          = aws_iam_role.sga_schema_migrator.arn
  handler       = "schema_migrator.handler"
  # MANDATORY: All Lambdas use arm64 + Python 3.13
  runtime       = "python3.13"
  architectures = ["arm64"]
  timeout       = 600  # 10 minutes for large schema migrations
  memory_size   = 512

  # Placeholder - actual code deployed via CI/CD
  filename         = data.archive_file.sga_schema_migrator_placeholder.output_path
  source_code_hash = data.archive_file.sga_schema_migrator_placeholder.output_base64sha256

  # VPC Configuration
  vpc_config {
    subnet_ids         = aws_subnet.sga_lambda[*].id
    security_group_ids = [aws_security_group.sga_lambda.id]
  }

  environment {
    variables = {
      RDS_PROXY_ENDPOINT = aws_db_proxy.sga.endpoint
      RDS_DATABASE_NAME  = "sga_inventory"
      RDS_PORT           = "5432"
      RDS_SECRET_ARN     = aws_secretsmanager_secret.sga_rds_master.arn
      AWS_REGION_NAME    = var.aws_region
      S3_BUCKET          = aws_s3_bucket.sga_documents.bucket
      LOG_LEVEL          = var.environment == "prod" ? "INFO" : "DEBUG"
    }
  }

  # Ensure VPC and RDS Proxy are ready
  depends_on = [
    aws_db_proxy_target.sga,
    aws_vpc_endpoint.sga_secretsmanager,
    aws_vpc_endpoint.sga_sts
  ]

  tags = {
    Name        = "${local.name_prefix}-sga-schema-migrator"
    Module      = "SGA"
    Feature     = "Schema Migration"
    Description = "Lambda for PostgreSQL schema migrations"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "sga_schema_migrator" {
  name              = "/aws/lambda/${aws_lambda_function.sga_schema_migrator.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "${local.name_prefix}-sga-schema-migrator-logs"
    Module      = "SGA"
    Feature     = "Schema Migration"
    Description = "Logs for PostgreSQL schema migrator Lambda"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_schema_migrator_lambda_arn" {
  description = "Lambda ARN for PostgreSQL schema migrator"
  value       = aws_lambda_function.sga_schema_migrator.arn
}

output "sga_schema_migrator_lambda_name" {
  description = "Lambda function name for PostgreSQL schema migrator"
  value       = aws_lambda_function.sga_schema_migrator.function_name
}
