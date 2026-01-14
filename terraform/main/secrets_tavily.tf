# =============================================================================
# AWS Secrets Manager - Tavily API Key for Equipment Enrichment
# =============================================================================
# Securely stores the Tavily API key for the Equipment Enrichment module.
# Used by AgentCore Gateway to authenticate with Tavily API.
#
# Architecture:
# - EnrichmentAgent -> AgentCore Gateway -> Tavily API
# - Gateway reads API key from Secrets Manager (credentialProviderType: GATEWAY_IAM_ROLE)
# - Agents NEVER access this secret directly (Gateway-first pattern)
#
# Reference:
# - PRD: product-development/current-feature/PRD-tavily-enrichment.md
# - CLAUDE.md MCP ACCESS POLICY: All MCP tools via AgentCore Gateway
# =============================================================================

# =============================================================================
# Tavily API Secret
# =============================================================================

resource "aws_secretsmanager_secret" "tavily_api_key" {
  name        = "${var.project_name}/tavily/api-key"
  description = "Tavily API key for equipment data enrichment via AgentCore Gateway"

  # Allow recovery for 7 days (minimum) to prevent accidental deletion
  recovery_window_in_days = 7

  tags = {
    Name        = "Faiston Tavily API Key"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
    Purpose     = "AI-optimized search for equipment specs and documentation"
    Access      = "AgentCore Gateway only"
  }
}

# =============================================================================
# Secret Value (Initial Setup)
# =============================================================================
# NOTE: In production, use `aws secretsmanager put-secret-value` to set the
# actual API key. This resource creates the placeholder.
#
# After Terraform apply, run:
# aws secretsmanager put-secret-value \
#   --secret-id faiston-one/tavily/api-key \
#   --secret-string '{"api_key": "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"}' \
#   --profile faiston-aio

resource "aws_secretsmanager_secret_version" "tavily_api_key" {
  secret_id = aws_secretsmanager_secret.tavily_api_key.id

  # Initial placeholder - will be updated with actual key via CLI
  # Using JSON format for extensibility (future: add rate limit config, etc.)
  secret_string = jsonencode({
    api_key = "PLACEHOLDER_REPLACE_VIA_CLI"
    tier    = "production"
    usage   = "equipment-enrichment"
  })

  lifecycle {
    # Prevent Terraform from overwriting manually-set secret values
    ignore_changes = [secret_string]
  }
}

# =============================================================================
# IAM Policy for Gateway to Read Tavily Secret
# =============================================================================
# Allows AgentCore Gateway role to retrieve the Tavily API key

data "aws_iam_policy_document" "gateway_tavily_secret_access" {
  statement {
    sid    = "AllowTavilySecretRead"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [
      aws_secretsmanager_secret.tavily_api_key.arn
    ]
  }
}

resource "aws_iam_role_policy" "gateway_tavily_secret" {
  name   = "${var.project_name}-gateway-tavily-secret-policy"
  role   = aws_iam_role.sga_agentcore_gateway.id
  policy = data.aws_iam_policy_document.gateway_tavily_secret_access.json
}

# =============================================================================
# Outputs
# =============================================================================

output "tavily_secret_arn" {
  description = "ARN of the Tavily API key secret"
  value       = aws_secretsmanager_secret.tavily_api_key.arn
}

output "tavily_secret_name" {
  description = "Name of the Tavily API key secret"
  value       = aws_secretsmanager_secret.tavily_api_key.name
}

# =============================================================================
# Post-Deployment Instructions
# =============================================================================
# After running `terraform apply`, set the actual API key:
#
# aws secretsmanager put-secret-value \
#   --secret-id faiston-one/tavily/api-key \
#   --secret-string '{"api_key": "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"}' \
#   --profile faiston-aio
#
# Verify:
# aws secretsmanager get-secret-value \
#   --secret-id faiston-one/tavily/api-key \
#   --profile faiston-aio
# =============================================================================
