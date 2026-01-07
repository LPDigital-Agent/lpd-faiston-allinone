# =============================================================================
# IAM Roles and Policies for Bedrock Knowledge Base (Equipment Documentation)
# =============================================================================
# Permissions for:
# - Bedrock Knowledge Base to access S3 bucket (document ingestion)
# - Bedrock KB to invoke embedding model (Titan v2)
# - SGA AgentCore to query Knowledge Base (RetrieveAndGenerate)
# - SGA AgentCore to upload documents to equipment docs bucket
#
# Security Principles:
# - Least privilege access
# - Service-specific trust policies
# - Condition-based restrictions
# =============================================================================

# =============================================================================
# IAM Role for Bedrock Knowledge Base Execution
# =============================================================================
# This role is assumed by Bedrock KB service for document ingestion

data "aws_iam_policy_document" "bedrock_kb_assume_role" {
  statement {
    sid    = "BedrockKBAssumeRole"
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
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"]
    }
  }
}

resource "aws_iam_role" "bedrock_kb_equipment" {
  name               = "${var.project_name}-bedrock-kb-equipment-role"
  assume_role_policy = data.aws_iam_policy_document.bedrock_kb_assume_role.json

  tags = {
    Name    = "Faiston Bedrock KB Equipment Documentation Role"
    Module  = "Gestao de Ativos"
    Feature = "Knowledge Base"
  }
}

# =============================================================================
# S3 Access Policy for Bedrock KB (Document Ingestion)
# =============================================================================
# Allows Bedrock KB to read documents from the equipment docs bucket

data "aws_iam_policy_document" "bedrock_kb_s3_access" {
  statement {
    sid    = "S3EquipmentDocsReadAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.sga_equipment_docs.arn,
      "${aws_s3_bucket.sga_equipment_docs.arn}/*"
    ]
  }
}

resource "aws_iam_role_policy" "bedrock_kb_s3" {
  name   = "${var.project_name}-bedrock-kb-s3-policy"
  role   = aws_iam_role.bedrock_kb_equipment.id
  policy = data.aws_iam_policy_document.bedrock_kb_s3_access.json
}

# =============================================================================
# Embedding Model Invocation Policy for Bedrock KB
# =============================================================================
# Allows Bedrock KB to invoke Titan Embeddings v2 for vectorization

data "aws_iam_policy_document" "bedrock_kb_model_invoke" {
  statement {
    sid    = "BedrockEmbeddingModelInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel"
    ]
    resources = [
      # Amazon Titan Text Embeddings v2
      "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0",
      # Also allow Titan v1 as fallback
      "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"
    ]
  }
}

resource "aws_iam_role_policy" "bedrock_kb_model" {
  name   = "${var.project_name}-bedrock-kb-model-policy"
  role   = aws_iam_role.bedrock_kb_equipment.id
  policy = data.aws_iam_policy_document.bedrock_kb_model_invoke.json
}

# =============================================================================
# Additional S3 Access for SGA AgentCore (Equipment Docs Upload)
# =============================================================================
# Allows EquipmentResearchAgent to upload documents to equipment docs bucket

data "aws_iam_policy_document" "sga_agentcore_equipment_docs_s3" {
  # Object operations (GET, PUT, DELETE)
  statement {
    sid    = "S3EquipmentDocsObjectAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      "${aws_s3_bucket.sga_equipment_docs.arn}/*"
    ]
  }

  # ListBucket permission (for listing documents by prefix)
  statement {
    sid    = "S3EquipmentDocsBucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.sga_equipment_docs.arn
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_equipment_docs_s3" {
  name   = "${var.project_name}-sga-equipment-docs-s3-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_equipment_docs_s3.json
}

# =============================================================================
# Knowledge Base Query Policy for SGA AgentCore
# =============================================================================
# Allows NEXO to query the Knowledge Base via RetrieveAndGenerate

data "aws_iam_policy_document" "sga_agentcore_kb_query" {
  statement {
    sid    = "BedrockKBRetrieveAccess"
    effect = "Allow"
    actions = [
      "bedrock:Retrieve",
      "bedrock:RetrieveAndGenerate"
    ]
    resources = [
      # Allow querying any knowledge base in this account
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
    ]
  }

  # Also need model invocation for RetrieveAndGenerate
  statement {
    sid    = "BedrockKBModelInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      # Gemini models via cross-region inference (per CLAUDE.md)
      "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*",
      # Claude as fallback for RAG generation
      "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-sonnet*",
      "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-haiku*"
    ]
  }
}

resource "aws_iam_role_policy" "sga_agentcore_kb_query" {
  name   = "${var.project_name}-sga-kb-query-policy"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.sga_agentcore_kb_query.json
}

# =============================================================================
# Outputs
# =============================================================================

output "bedrock_kb_role_arn" {
  description = "ARN of the Bedrock KB execution role for equipment documentation"
  value       = aws_iam_role.bedrock_kb_equipment.arn
}

output "bedrock_kb_role_name" {
  description = "Name of the Bedrock KB execution role"
  value       = aws_iam_role.bedrock_kb_equipment.name
}
