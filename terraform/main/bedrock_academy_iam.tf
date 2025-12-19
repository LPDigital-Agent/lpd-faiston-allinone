# =============================================================================
# IAM Roles and Policies for Academy AgentCore
# =============================================================================
# Permissions for:
# - Bedrock model invocation (Claude Sonnet 4.5, Gemini)
# - AgentCore Memory operations (STM + LTM)
# - S3 bucket access (audio, slides, videos, trainings)
# - DynamoDB access (trainings table)
# - SSM Parameter Store access (API keys)
# - CloudWatch Logs for observability
#
# Note: The AgentCore CLI creates its own execution role with pattern:
# AmazonBedrockAgentCoreSDKRuntime-{region}-{suffix}
# We attach S3/DynamoDB/SSM policies to THIS role after first deployment.
# =============================================================================

# Note: data "aws_caller_identity" "current" is defined in locals.tf

# =============================================================================
# IAM Role for AgentCore Execution (Terraform-managed)
# =============================================================================
# This role is created by Terraform for reference but the actual execution
# uses the CLI-created role. Useful for local testing.

data "aws_iam_policy_document" "academy_agentcore_assume_role" {
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

resource "aws_iam_role" "academy_agentcore_execution" {
  name               = "${var.project_name}-academy-agentcore-role"
  assume_role_policy = data.aws_iam_policy_document.academy_agentcore_assume_role.json

  tags = {
    Name    = "Faiston Academy AgentCore Execution Role"
    Feature = "Academy"
  }
}

# =============================================================================
# Bedrock Model Invocation Policy
# =============================================================================
# Allows invoking Claude Sonnet 4.5 and cross-region inference profiles

data "aws_iam_policy_document" "academy_bedrock_invoke" {
  statement {
    sid    = "BedrockModelInvocation"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      # Claude Sonnet 4.5 - US inference profile routes across multiple regions
      "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
      # Claude 3.5 Sonnet - Fallback
      "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
      "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
      "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
      # Cross-region inference profiles
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*"
    ]
  }
}

resource "aws_iam_role_policy" "academy_agentcore_bedrock" {
  name   = "${var.project_name}-academy-bedrock-policy"
  role   = aws_iam_role.academy_agentcore_execution.id
  policy = data.aws_iam_policy_document.academy_bedrock_invoke.json
}

# =============================================================================
# AgentCore Memory Policy
# =============================================================================
# Allows all memory operations for STM + LTM
# Memory ID will be created when AgentCore agents are deployed

data "aws_iam_policy_document" "academy_agentcore_memory" {
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

resource "aws_iam_role_policy" "academy_agentcore_memory" {
  name   = "${var.project_name}-academy-memory-policy"
  role   = aws_iam_role.academy_agentcore_execution.id
  policy = data.aws_iam_policy_document.academy_agentcore_memory.json
}

# =============================================================================
# CloudWatch Logs Policy
# =============================================================================
# Allows agents to write logs for observability

data "aws_iam_policy_document" "academy_agentcore_logs" {
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

resource "aws_iam_role_policy" "academy_agentcore_logs" {
  name   = "${var.project_name}-academy-logs-policy"
  role   = aws_iam_role.academy_agentcore_execution.id
  policy = data.aws_iam_policy_document.academy_agentcore_logs.json
}

# =============================================================================
# S3 Bucket Access Policy
# =============================================================================
# Allows agents to store generated files in Academy buckets

data "aws_iam_policy_document" "academy_agentcore_s3" {
  statement {
    sid    = "S3AcademyBucketAccess"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject"
    ]
    resources = [
      "${aws_s3_bucket.academy_audio.arn}/*",
      "${aws_s3_bucket.academy_videos.arn}/*",
      "${aws_s3_bucket.academy_slides.arn}/*",
      "${aws_s3_bucket.academy_trainings.arn}/*"
    ]
  }

  # ListBucket permission for trainings (needed to list documents)
  statement {
    sid    = "S3AcademyTrainingsBucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.academy_trainings.arn
    ]
  }
}

resource "aws_iam_role_policy" "academy_agentcore_s3" {
  name   = "${var.project_name}-academy-s3-policy"
  role   = aws_iam_role.academy_agentcore_execution.id
  policy = data.aws_iam_policy_document.academy_agentcore_s3.json
}

# =============================================================================
# SSM Parameter Store Access Policy
# =============================================================================
# Allows reading API keys for external services

data "aws_iam_policy_document" "academy_agentcore_ssm" {
  statement {
    sid    = "SSMAcademyParameterAccess"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      aws_ssm_parameter.academy_google_api_key.arn,
      aws_ssm_parameter.academy_elevenlabs_api_key.arn,
      aws_ssm_parameter.academy_heygen_api_key.arn,
      aws_ssm_parameter.academy_youtube_api_key.arn
    ]
  }
}

resource "aws_iam_role_policy" "academy_agentcore_ssm" {
  name   = "${var.project_name}-academy-ssm-policy"
  role   = aws_iam_role.academy_agentcore_execution.id
  policy = data.aws_iam_policy_document.academy_agentcore_ssm.json
}

# =============================================================================
# DynamoDB Access Policy
# =============================================================================
# Allows operations on Academy trainings table

data "aws_iam_policy_document" "academy_agentcore_dynamodb" {
  statement {
    sid    = "DynamoDBAcademyTrainingsAccess"
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
      aws_dynamodb_table.academy_trainings.arn,
      "${aws_dynamodb_table.academy_trainings.arn}/index/*"
    ]
  }
}

resource "aws_iam_role_policy" "academy_agentcore_dynamodb" {
  name   = "${var.project_name}-academy-dynamodb-policy"
  role   = aws_iam_role.academy_agentcore_execution.id
  policy = data.aws_iam_policy_document.academy_agentcore_dynamodb.json
}

# =============================================================================
# Policies for AgentCore CLI-Created Role
# =============================================================================
# The AgentCore CLI creates its own execution role. After first deployment,
# we need to attach these policies to that role.
#
# Role name pattern: AmazonBedrockAgentCoreSDKRuntime-{region}-{suffix}
# The suffix is generated during first deployment.
#
# IMPORTANT: After deploying the first agent, update the variable
# `academy_agentcore_cli_role_name` with the actual role name, then
# uncomment and apply the policies below.
# =============================================================================

# Uncomment after first AgentCore deployment and set the role name variable:
#
# resource "aws_iam_role_policy" "academy_cli_s3" {
#   name   = "${var.project_name}-academy-cli-s3-policy"
#   role   = var.academy_agentcore_cli_role_name
#   policy = data.aws_iam_policy_document.academy_agentcore_s3.json
# }
#
# resource "aws_iam_role_policy" "academy_cli_dynamodb" {
#   name   = "${var.project_name}-academy-cli-dynamodb-policy"
#   role   = var.academy_agentcore_cli_role_name
#   policy = data.aws_iam_policy_document.academy_agentcore_dynamodb.json
# }
#
# resource "aws_iam_role_policy" "academy_cli_ssm" {
#   name   = "${var.project_name}-academy-cli-ssm-policy"
#   role   = var.academy_agentcore_cli_role_name
#   policy = data.aws_iam_policy_document.academy_agentcore_ssm.json
# }

# =============================================================================
# Outputs
# =============================================================================

output "academy_agentcore_role_arn" {
  description = "ARN of the Terraform-managed AgentCore execution role"
  value       = aws_iam_role.academy_agentcore_execution.arn
}

output "academy_agentcore_role_name" {
  description = "Name of the Terraform-managed AgentCore execution role"
  value       = aws_iam_role.academy_agentcore_execution.name
}
