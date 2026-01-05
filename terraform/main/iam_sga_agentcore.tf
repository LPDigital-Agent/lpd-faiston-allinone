# =============================================================================
# IAM Roles and Policies for SGA AgentCore (Gestão de Estoque)
# =============================================================================
# Permissions for:
# - Bedrock/Gemini model invocation
# - AgentCore Memory operations (STM + LTM)
# - DynamoDB access (inventory, HIL tasks, audit log tables)
# - S3 bucket access (documents)
# - SSM Parameter Store access (API keys)
# - CloudWatch Logs for observability
#
# Security Principles:
# - Least privilege access
# - Separate policies per resource type
# - No wildcard resources where possible
# - Condition-based restrictions
# =============================================================================

# Note: data "aws_caller_identity" "current" is defined in locals.tf

# =============================================================================
# IAM Role for SGA AgentCore Execution
# =============================================================================

data "aws_iam_policy_document" "sga_agentcore_assume_role" {
  statement {
    sid    = "AgentCoreAssumeRole"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "sga_agentcore_execution" {
  name               = "${var.project_name}-sga-agentcore-role"
  assume_role_policy = data.aws_iam_policy_document.sga_agentcore_assume_role.json

  tags = {
    Name    = "Faiston SGA AgentCore Execution Role"
    Module  = "Gestao de Ativos"
    Feature = "Gestao de Estoque"
  }
}

# =============================================================================
# Bedrock Model Invocation Policy (Gemini via Vertex AI)
# =============================================================================
# Note: Gemini 3.0 models are accessed via Google Vertex AI
# This policy is for any Bedrock fallback models if needed

data "aws_iam_policy_document" "sga_bedrock_invoke" {
  statement {
    sid    = "BedrockModelInvocation"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      # Claude models (fallback if Gemini unavailable)
      "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      # Cross-region inference profiles
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*"
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_bedrock" {
  name   = "${var.project_name}-sga-bedrock-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_bedrock_invoke.json
}

# =============================================================================
# AgentCore Memory Policy
# =============================================================================
# Allows all memory operations for STM + LTM

data "aws_iam_policy_document" "sga_agentcore_memory" {
  statement {
    sid    = "AgentCoreMemoryOperations"
    effect = "Allow"
    actions = [
      # Memory CRUD operations
      "bedrock:GetMemory",
      "bedrock:ListMemories",
      # Event operations (STM)
      "bedrock:CreateMemoryEvent",
      "bedrock:GetMemoryEvent",
      "bedrock:ListMemoryEvents",
      "bedrock:DeleteMemoryEvent",
      # Retrieval operations (semantic search)
      "bedrock:RetrieveMemory",
      "bedrock:RetrieveAndGenerate"
    ]
    resources = [
      # Allow operations on any memory created for this project
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:memory/*"
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_memory" {
  name   = "${var.project_name}-sga-memory-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_memory.json
}

# =============================================================================
# CloudWatch Logs Policy
# =============================================================================

data "aws_iam_policy_document" "sga_agentcore_logs" {
  statement {
    sid    = "AgentCoreLogging"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams"
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vendedlogs/bedrock-agentcore/*"
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_logs" {
  name   = "${var.project_name}-sga-logs-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_logs.json
}

# =============================================================================
# S3 Bucket Access Policy
# =============================================================================

data "aws_iam_policy_document" "sga_agentcore_s3" {
  # Object operations (GET, PUT, DELETE)
  statement {
    sid    = "S3SGADocumentsObjectAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      "${aws_s3_bucket.sga_documents.arn}/*"
    ]
  }

  # ListBucket permission (for listing NFs, evidences)
  statement {
    sid    = "S3SGADocumentsBucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.sga_documents.arn
    ]
  }

  # Pre-signed URL generation requires GetObject
  statement {
    sid    = "S3SGADocumentsPresigned"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = [
      "${aws_s3_bucket.sga_documents.arn}/*"
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_s3" {
  name   = "${var.project_name}-sga-s3-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_s3.json
}

# =============================================================================
# DynamoDB Access Policy
# =============================================================================
# Full access to all SGA tables (inventory, HIL tasks, audit log)

data "aws_iam_policy_document" "sga_agentcore_dynamodb" {
  # Main inventory table operations
  statement {
    sid    = "DynamoDBSGAInventoryAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem"
    ]
    resources = [
      aws_dynamodb_table.sga_inventory.arn,
      "${aws_dynamodb_table.sga_inventory.arn}/index/*"
    ]
  }

  # HIL tasks table operations
  statement {
    sid    = "DynamoDBSGAHILTasksAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem"
    ]
    resources = [
      aws_dynamodb_table.sga_hil_tasks.arn,
      "${aws_dynamodb_table.sga_hil_tasks.arn}/index/*"
    ]
  }

  # Audit log table operations (APPEND-ONLY: no DeleteItem)
  statement {
    sid    = "DynamoDBSGAAuditLogAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem"
      # Note: No DeleteItem or UpdateItem for audit immutability
    ]
    resources = [
      aws_dynamodb_table.sga_audit_log.arn,
      "${aws_dynamodb_table.sga_audit_log.arn}/index/*"
    ]
  }

  # DynamoDB Streams for real-time projections
  statement {
    sid    = "DynamoDBSGAStreamsAccess"
    effect = "Allow"
    actions = [
      "dynamodb:DescribeStream",
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator",
      "dynamodb:ListStreams"
    ]
    resources = [
      aws_dynamodb_table.sga_inventory.stream_arn
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_dynamodb" {
  name   = "${var.project_name}-sga-dynamodb-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_dynamodb.json
}

# =============================================================================
# AgentCore Gateway Invoke Policy
# =============================================================================
# Allows agents to invoke tools via AgentCore Gateway MCP endpoint
# Required for PostgreSQL MCP tools communication

data "aws_iam_policy_document" "sga_agentcore_gateway" {
  statement {
    sid    = "AgentCoreGatewayInvoke"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:InvokeGateway",
      "bedrock-agentcore:ListGateways",
      "bedrock-agentcore:GetGateway"
    ]
    resources = [
      # Allow invoking any gateway in this account/region
      "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:gateway/*"
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_gateway" {
  name   = "${var.project_name}-sga-gateway-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_gateway.json
}

# =============================================================================
# SSM Parameter Store Access Policy
# =============================================================================
# Access to API keys for external services (Google API for Gemini)

data "aws_iam_policy_document" "sga_agentcore_ssm" {
  statement {
    sid    = "SSMSGAParameterAccess"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      # Google API key (for Gemini 3.0)
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/sga/*",
      # Also allow access to shared Google API key from Academy
      aws_ssm_parameter.academy_google_api_key.arn
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_ssm" {
  name   = "${var.project_name}-sga-ssm-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_ssm.json
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_agentcore_role_arn" {
  description = "ARN of the SGA AgentCore execution role"
  value       = aws_iam_role.sga_agentcore_execution.arn
}

output "sga_agentcore_role_name" {
  description = "Name of the SGA AgentCore execution role"
  value       = aws_iam_role.sga_agentcore_execution.name
}
