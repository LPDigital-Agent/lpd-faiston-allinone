# =============================================================================
# AWS Secrets Manager - POSTAL Service Credentials
# =============================================================================
# Securely stores POSTAL API credentials for inventory integration.
# Used by AgentCore Gateway to authenticate with POSTAL service.
#
# Architecture:
# - InventoryAgent -> AgentCore Gateway -> POSTAL API
# - Gateway reads credentials from Secrets Manager (credentialProviderType: GATEWAY_IAM_ROLE)
# - Agents NEVER access this secret directly (Gateway-first pattern)
#
# Credentials stored:
# - usuario: POSTAL username
# - token: POSTAL authentication token
# - id_perfil: POSTAL profile ID
# =============================================================================

# =============================================================================
# POSTAL Credentials Secret
# =============================================================================

resource "aws_secretsmanager_secret" "postal_credentials" {
  name        = "${var.project_name}/postal/credentials"
  description = "POSTAL service credentials for inventory integration via AgentCore Gateway"

  # Allow recovery for 7 days (minimum) to prevent accidental deletion
  recovery_window_in_days = 7

  tags = {
    Name        = "Faiston POSTAL Credentials"
    Environment = var.environment
    Module      = "SGA"
    Feature     = "Inventory Integration"
    Purpose     = "POSTAL API authentication for inventory operations"
    Access      = "AgentCore Gateway only"
  }
}

# =============================================================================
# Secret Value (Initial Setup)
# =============================================================================
# NOTE: In production, use `aws secretsmanager put-secret-value` to set the
# actual credentials. This resource creates the placeholder.
#
# After Terraform apply, run:
# aws secretsmanager put-secret-value \
#   --secret-id faiston-one/postal/credentials \
#   --secret-string '{"usuario": "YOUR_USUARIO", "token": "YOUR_TOKEN", "id_perfil": "YOUR_ID_PERFIL"}' \
#   --profile faiston-aio

resource "aws_secretsmanager_secret_version" "postal_credentials" {
  secret_id = aws_secretsmanager_secret.postal_credentials.id

  # Initial placeholder - will be updated with actual credentials via CLI
  # Using JSON format for extensibility
  secret_string = jsonencode({
    usuario   = var.postal_usuario
    token     = var.postal_token
    id_perfil = var.postal_id_perfil
  })

  lifecycle {
    # Prevent Terraform from overwriting manually-set secret values
    ignore_changes = [secret_string]
  }
}

# =============================================================================
# IAM Policy for Gateway to Read POSTAL Secret
# =============================================================================
# Allows AgentCore Gateway role to retrieve the POSTAL credentials

data "aws_iam_policy_document" "gateway_postal_secret_access" {
  statement {
    sid    = "AllowPostalSecretRead"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [
      aws_secretsmanager_secret.postal_credentials.arn
    ]
  }
}

resource "aws_iam_role_policy" "gateway_postal_secret" {
  name   = "${var.project_name}-gateway-postal-secret-policy"
  role   = aws_iam_role.sga_agentcore_gateway.id
  policy = data.aws_iam_policy_document.gateway_postal_secret_access.json
}

# =============================================================================
# Outputs
# =============================================================================

output "postal_secret_arn" {
  description = "ARN of the POSTAL credentials secret"
  value       = aws_secretsmanager_secret.postal_credentials.arn
}

output "postal_secret_name" {
  description = "Name of the POSTAL credentials secret"
  value       = aws_secretsmanager_secret.postal_credentials.name
}

# =============================================================================
# Post-Deployment Instructions
# =============================================================================
# After running `terraform apply`, set the actual credentials:
#
# aws secretsmanager put-secret-value \
#   --secret-id faiston-one/postal/credentials \
#   --secret-string '{"usuario": "YOUR_USUARIO", "token": "YOUR_TOKEN", "id_perfil": "YOUR_ID_PERFIL"}' \
#   --profile faiston-aio
#
# Verify:
# aws secretsmanager get-secret-value \
#   --secret-id faiston-one/postal/credentials \
#   --profile faiston-aio
# =============================================================================
