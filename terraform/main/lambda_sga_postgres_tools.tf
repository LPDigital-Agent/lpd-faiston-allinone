# =============================================================================
# Lambda Function for SGA PostgreSQL MCP Tools
# =============================================================================
# Lambda function that handles PostgreSQL tool calls from AgentCore Gateway.
#
# Architecture:
# AgentCore Gateway → Lambda (this) → RDS Proxy → Aurora PostgreSQL
#
# Tools Provided:
# - sga_list_inventory: List assets with filters
# - sga_get_balance: Get stock balance
# - sga_search_assets: Search by serial/PN/description
# - sga_get_asset_timeline: Asset history
# - sga_get_movements: Movement list
# - sga_get_pending_tasks: HIL tasks
# - sga_create_movement: Create movement
# - sga_reconcile_sap: SAP comparison
#
# Security:
# - VPC-attached (private subnets)
# - IAM auth to RDS Proxy
# - No internet access (uses VPC endpoints)
# =============================================================================

# =============================================================================
# IAM Role for Lambda
# =============================================================================

resource "aws_iam_role" "sga_postgres_tools" {
  name = "${local.name_prefix}-sga-postgres-tools-role"

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
    Name        = "${local.name_prefix}-sga-postgres-tools-role"
    Module      = "SGA"
    Feature     = "MCP Tools"
    Description = "IAM role for PostgreSQL MCP tools Lambda"
  }
}

# VPC access policy
resource "aws_iam_role_policy_attachment" "sga_postgres_tools_vpc" {
  role       = aws_iam_role.sga_postgres_tools.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# RDS IAM auth policy
resource "aws_iam_role_policy" "sga_postgres_tools_rds" {
  name = "${local.name_prefix}-sga-postgres-tools-rds"
  role = aws_iam_role.sga_postgres_tools.id

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

# CloudWatch Logs policy
resource "aws_iam_role_policy" "sga_postgres_tools_logs" {
  name = "${local.name_prefix}-sga-postgres-tools-logs"
  role = aws_iam_role.sga_postgres_tools.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}-sga-postgres-tools:*"
    }]
  })
}

# =============================================================================
# Lambda Function
# =============================================================================

# Placeholder for deployment package
# Actual code will be deployed via GitHub Actions
data "archive_file" "sga_postgres_tools_placeholder" {
  type        = "zip"
  output_path = "${path.module}/sga_postgres_tools_placeholder.zip"

  source {
    content  = <<EOF
# Placeholder - actual code deployed via GitHub Actions
def handler(event, context):
    return {"error": "Placeholder - deploy actual code via GitHub Actions"}
EOF
    filename = "handler.py"
  }
}

resource "aws_lambda_function" "sga_postgres_tools" {
  function_name = "${local.name_prefix}-sga-postgres-tools"
  description   = "PostgreSQL MCP tools for SGA inventory"
  role          = aws_iam_role.sga_postgres_tools.arn
  handler       = "postgres_tools_lambda.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 512

  # Placeholder - actual code deployed via CI/CD
  filename         = data.archive_file.sga_postgres_tools_placeholder.output_path
  source_code_hash = data.archive_file.sga_postgres_tools_placeholder.output_base64sha256

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
      AWS_REGION_NAME    = var.aws_region
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
    Name        = "${local.name_prefix}-sga-postgres-tools"
    Module      = "SGA"
    Feature     = "MCP Tools"
    Description = "Lambda for PostgreSQL MCP tool execution"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "sga_postgres_tools" {
  name              = "/aws/lambda/${aws_lambda_function.sga_postgres_tools.function_name}"
  retention_in_days = 30

  tags = {
    Name        = "${local.name_prefix}-sga-postgres-tools-logs"
    Module      = "SGA"
    Feature     = "MCP Tools"
    Description = "Logs for PostgreSQL MCP tools Lambda"
  }
}

# =============================================================================
# Lambda Permission for AgentCore Gateway
# =============================================================================

resource "aws_lambda_permission" "sga_postgres_tools_gateway" {
  statement_id  = "AllowAgentCoreGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sga_postgres_tools.function_name
  principal     = "bedrock-agentcore.amazonaws.com"
  source_arn    = "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:gateway/*"
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_postgres_tools_lambda_arn" {
  description = "Lambda ARN for PostgreSQL MCP tools"
  value       = aws_lambda_function.sga_postgres_tools.arn
}

output "sga_postgres_tools_lambda_name" {
  description = "Lambda function name for PostgreSQL MCP tools"
  value       = aws_lambda_function.sga_postgres_tools.function_name
}
