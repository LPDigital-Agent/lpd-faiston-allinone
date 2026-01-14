# =============================================================================
# SSM Parameter for Tavily Gateway Configuration
# =============================================================================
# Stores Tavily Gateway configuration for runtime access by agents.
# This enables configuration changes without code redeployment.
#
# Gateway Details (Created via AWS Console - Built-in Tavily Template):
#   Gateway ID: faiston-one-sga-gateway-tavily-se9zyznpyo
#   Auth Type: CUSTOM_JWT (Cognito OAuth2)
#   Target Name: target-tavily
#
# Usage in Python:
#   import boto3
#   import json
#   ssm = boto3.client('ssm')
#   config = json.loads(ssm.get_parameter(
#       Name='/faiston-one/sga/tavily-gateway/config'
#   )['Parameter']['Value'])
#
# Reference:
# - PRD: product-development/current-feature/PRD-tavily-enrichment.md
# - Client: server/agentcore-inventory/tools/cognito_mcp_client.py
# =============================================================================

# =============================================================================
# Tavily Gateway Configuration Parameter
# =============================================================================
resource "aws_ssm_parameter" "tavily_gateway_config" {
  name        = "/${var.project_name}/sga/tavily-gateway/config"
  description = "Tavily Gateway configuration for equipment enrichment"
  type        = "String"

  value = jsonencode({
    # Gateway identifiers
    gateway_id  = "faiston-one-sga-gateway-tavily-se9zyznpyo"
    gateway_url = "https://faiston-one-sga-gateway-tavily-se9zyznpyo.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp"

    # MCP target configuration
    target_name = "target-tavily"

    # Cognito OAuth2 configuration
    cognito_pool      = "us-east-2_SrvZGerqb"
    cognito_client_id = "5nq8g72i81uc25dd966tht601p"
    token_url         = "https://my-domain-ze9v2zyh.auth.us-east-2.amazoncognito.com/oauth2/token"

    # Available MCP tools (built-in Tavily template)
    # Note: crawl and map are NOT available in built-in template
    available_tools = [
      "target-tavily___TavilySearchPost",
      "target-tavily___TavilySearchExtract"
    ]

    # AWS region
    region = var.aws_region
  })

  tags = {
    Name        = "${var.project_name}-tavily-gateway-config"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
    Purpose     = "Runtime configuration for Tavily Gateway access"
  }
}

# =============================================================================
# Cognito Client Secret ARN Parameter
# =============================================================================
# The actual secret is stored in Secrets Manager (created via AWS Console
# when setting up the Tavily Gateway with built-in template).
# This parameter stores the ARN for agent code to reference.
#
# Note: The secret itself is managed by AWS AgentCore's Token Vault,
# accessible via the credential provider ARN.

resource "aws_ssm_parameter" "tavily_cognito_secret_arn" {
  name        = "/${var.project_name}/sga/tavily-gateway/cognito-secret-arn"
  description = "ARN of Cognito client secret in Secrets Manager"
  type        = "String"

  # This secret was created by AWS Console when setting up the Gateway
  # The actual secret name follows AWS AgentCore's naming convention
  value = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/tavily-gateway/cognito-client-secret"

  tags = {
    Name        = "${var.project_name}-tavily-cognito-secret-arn"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
    Purpose     = "Reference to Cognito client secret for Tavily Gateway"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "tavily_gateway_config_ssm" {
  description = "SSM parameter path for Tavily Gateway configuration"
  value       = aws_ssm_parameter.tavily_gateway_config.name
}

output "tavily_gateway_config_arn" {
  description = "SSM parameter ARN for Tavily Gateway configuration"
  value       = aws_ssm_parameter.tavily_gateway_config.arn
}

output "tavily_cognito_secret_ssm" {
  description = "SSM parameter path for Cognito secret ARN"
  value       = aws_ssm_parameter.tavily_cognito_secret_arn.name
}

# =============================================================================
# IAM Policy for Agents to Read Tavily Config
# =============================================================================
# This policy allows AgentCore agents to read the Tavily Gateway configuration.
# Attach this policy to the agent execution role.

data "aws_iam_policy_document" "tavily_gateway_config_read" {
  statement {
    sid    = "AllowReadTavilyGatewayConfig"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      aws_ssm_parameter.tavily_gateway_config.arn,
      aws_ssm_parameter.tavily_cognito_secret_arn.arn
    ]
  }
}

resource "aws_iam_role_policy" "agentcore_tavily_config" {
  name   = "${var.project_name}-agentcore-tavily-config"
  role   = aws_iam_role.sga_agentcore_execution.id
  policy = data.aws_iam_policy_document.tavily_gateway_config_read.json
}

# =============================================================================
# Usage Example (Python)
# =============================================================================
# from tools.tavily_gateway import TavilyGatewayFactory
#
# # Create client from SSM configuration
# tavily = TavilyGatewayFactory.create_from_ssm()
#
# # Or with explicit config
# tavily = TavilyGateway(
#     gateway_url="https://...",
#     token_url="https://...",
#     client_id="...",
#     client_secret="..." # from Secrets Manager
# )
#
# # Search for equipment specs
# result = tavily.search("Cisco C9200-24P specifications")
# =============================================================================
