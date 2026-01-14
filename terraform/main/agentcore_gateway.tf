# =============================================================================
# AgentCore Gateway for SGA Inventory
# =============================================================================
# AgentCore Gateway provides a unified MCP endpoint for AI agents.
#
# AUTHENTICATION ARCHITECTURE (AgentCore Identity Compliance):
# ┌─────────────────────────────────────────────────────────────────────┐
# │ FRONTEND (React/Next.js)                                            │
# │ └─ JWT Bearer Token (Cognito Access Token)                          │
# └──────────────────────────────┬──────────────────────────────────────┘
#                                │
#                                ▼ Authorization: Bearer {JWT}
# ┌─────────────────────────────────────────────────────────────────────┐
# │ AgentCore RUNTIME (faiston_asset_management-uSuLPsFQNH)             │
# │ └─ JWT Authorizer ENABLED (customJWTAuthorizer)                     │
# │    - discoveryUrl: cognito-idp.../openid-configuration              │
# │    - allowedClients: [7ovjm09dr94e52mpejvbu9v1cg]                   │
# │    - context.identity populated with JWT claims                     │
# └──────────────────────────────┬──────────────────────────────────────┘
#                                │
#                                ▼ SigV4 (IAM credentials)
# ┌─────────────────────────────────────────────────────────────────────┐
# │ AgentCore GATEWAY (faiston-one-sga-gateway-prod-qbnlm3ao63)         │
# │ └─ AWS_IAM auth (CORRECT - accessed by Runtime, not users)          │
# │    - Semantic search enabled                                        │
# │    - Routes to Lambda MCP targets                                   │
# └──────────────────────────────┬──────────────────────────────────────┘
#                                │
#                                ▼ IAM invoke
# ┌─────────────────────────────────────────────────────────────────────┐
# │ Lambda MCP Target (SGAPostgresTools)                                │
# └─────────────────────────────────────────────────────────────────────┘
#
# KEY POINTS:
# - JWT validation happens at RUNTIME level, NOT Gateway
# - Gateway uses AWS_IAM because it's backend-to-backend (Runtime → Gateway)
# - JWT Authorizer is configured via GitHub workflow (deploy-agentcore-inventory.yml)
# - Agents extract user identity from context.identity (JWT validated)
#
# Reference:
# - JWT config: .github/workflows/deploy-agentcore-inventory.yml:164-252
# - Identity utils: server/agentcore-inventory/shared/identity_utils.py
# - Cognito Pool: us-east-2_lkBXr4kjy
# - Cognito Client: 7ovjm09dr94e52mpejvbu9v1cg
# =============================================================================

# =============================================================================
# Data Source: Cognito User Pool
# =============================================================================
# Reference existing Cognito User Pool for JWT validation.
# If Cognito doesn't exist yet, these will need to be created.

# Placeholder for Cognito data source
# Uncomment when Cognito resources are available
# data "aws_cognito_user_pool" "main" {
#   user_pool_id = var.cognito_user_pool_id
# }

# =============================================================================
# IAM Role for AgentCore Gateway
# =============================================================================

resource "aws_iam_role" "sga_agentcore_gateway" {
  name = "${local.name_prefix}-sga-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock-agentcore.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${local.name_prefix}-sga-gateway-role"
    Module      = "SGA"
    Feature     = "AgentCore Gateway"
    Description = "IAM role for AgentCore Gateway"
  }
}

# Policy to invoke Lambda targets
resource "aws_iam_role_policy" "sga_agentcore_gateway_lambda" {
  name = "${local.name_prefix}-sga-gateway-lambda"
  role = aws_iam_role.sga_agentcore_gateway.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowLambdaInvoke"
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction"
      ]
      Resource = aws_lambda_function.sga_postgres_tools.arn
    }]
  })
}

# =============================================================================
# AgentCore Gateway (Created via boto3 API)
# =============================================================================
# NOTE: Gateway was created via boto3 API because Terraform resources were
# not available at deployment time. If recreating, use AWS CLI:
#
# aws bedrock-agentcore create-gateway \
#   --name "faiston-one-sga-gateway-prod" \
#   --authorization-configuration '{"authorizationType": "AWS_IAM"}' \
#   --semantic-search-configuration '{"semanticSearchEnabled": true}' \
#   --tags Module=SGA,Feature=AgentCore
#
# NOTE: AWS_IAM is correct for Gateway - JWT auth is on the Runtime!

# =============================================================================
# Gateway Configuration (Created via boto3 - January 2026)
# =============================================================================
# Gateway was created via boto3 API as Terraform resources are not yet available.
# The following values document the actual deployed Gateway:
#
# Gateway ID: faiston-one-sga-gateway-prod-qbnlm3ao63
# Gateway URL: https://faiston-one-sga-gateway-prod-qbnlm3ao63.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp
# Target ID: SKVZZNCDKE
# Target Name: SGAPostgresTools
# Auth Type: AWS_IAM
#
# TAVILY TARGET (Equipment Enrichment - January 2026):
# Gateway now supports Tavily as native OpenAPI target for equipment data enrichment.
# Tavily provides AI-optimized search for specs, manuals, and documentation.
# Target ID: [TO_BE_CREATED_VIA_CLI]
# Target Name: TavilySearchMCP
# Auth Type: API Key (via Secrets Manager)
# =============================================================================

locals {
  sga_gateway_name = "${local.name_prefix}-sga-gateway"

  # Actual deployed gateway configuration
  sga_gateway_id  = "faiston-one-sga-gateway-prod-qbnlm3ao63"
  sga_gateway_url = "https://faiston-one-sga-gateway-prod-qbnlm3ao63.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp"
  sga_target_id   = "SKVZZNCDKE"
  sga_target_name = "SGAPostgresTools"

  # Tavily target configuration (to be created via CLI)
  tavily_target_name    = "TavilySearchMCP"
  tavily_target_id      = "PLACEHOLDER_UPDATE_AFTER_CREATION"
  tavily_api_secret_arn = aws_secretsmanager_secret.tavily_api_key.arn

  # Gateway configuration for reference
  sga_gateway_config = {
    gateway_id  = local.sga_gateway_id
    gateway_url = local.sga_gateway_url
    target_id   = local.sga_target_id
    target_name = local.sga_target_name
    auth_type   = "AWS_IAM"
    region      = var.aws_region
    # Tavily target (add after CLI creation)
    tavily_target_id   = local.tavily_target_id
    tavily_target_name = local.tavily_target_name
  }

  # Tool schema for inline definition
  sga_mcp_tools = [
    {
      name        = "sga_list_inventory"
      description = "Lista ativos e saldos no estoque com filtros opcionais"
      input_schema = {
        type = "object"
        properties = {
          location_id = { type = "string", description = "Filtro por código do local" }
          project_id  = { type = "string", description = "Filtro por código do projeto" }
          part_number = { type = "string", description = "Filtro por part number" }
          status      = { type = "string", enum = ["IN_STOCK", "IN_TRANSIT", "RESERVED", "INSTALLED"] }
          limit       = { type = "integer", default = 100, maximum = 1000 }
          offset      = { type = "integer", default = 0 }
        }
      }
    },
    {
      name        = "sga_get_balance"
      description = "Obtém saldo de estoque para um part number em um local"
      input_schema = {
        type     = "object"
        required = ["part_number"]
        properties = {
          part_number = { type = "string", description = "Part number a consultar" }
          location_id = { type = "string", description = "Filtro por local (opcional)" }
          project_id  = { type = "string", description = "Filtro por projeto (opcional)" }
        }
      }
    },
    {
      name        = "sga_search_assets"
      description = "Busca ativos por serial number, part number ou descrição"
      input_schema = {
        type     = "object"
        required = ["query"]
        properties = {
          query       = { type = "string", description = "Termo de busca (serial, PN ou descrição)" }
          search_type = { type = "string", enum = ["serial", "part_number", "description", "all"], default = "all" }
          limit       = { type = "integer", default = 50 }
        }
      }
    },
    {
      name        = "sga_get_asset_timeline"
      description = "Obtém histórico completo de um ativo (event sourcing)"
      input_schema = {
        type     = "object"
        required = ["identifier"]
        properties = {
          identifier      = { type = "string", description = "Asset ID ou serial number" }
          identifier_type = { type = "string", enum = ["asset_id", "serial_number"], default = "serial_number" }
          limit           = { type = "integer", default = 100 }
        }
      }
    },
    {
      name        = "sga_get_movements"
      description = "Lista movimentações com filtros por data, tipo e projeto"
      input_schema = {
        type = "object"
        properties = {
          start_date    = { type = "string", format = "date", description = "Data inicial (YYYY-MM-DD)" }
          end_date      = { type = "string", format = "date", description = "Data final (YYYY-MM-DD)" }
          movement_type = { type = "string", enum = ["ENTRADA", "SAIDA", "TRANSFERENCIA", "RESERVA", "LIBERACAO", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO", "EXPEDIÇÃO", "REVERSA"] }
          project_id    = { type = "string" }
          location_id   = { type = "string" }
          limit         = { type = "integer", default = 100 }
        }
      }
    },
    {
      name        = "sga_get_pending_tasks"
      description = "Lista tarefas pendentes de aprovação (HIL)"
      input_schema = {
        type = "object"
        properties = {
          task_type   = { type = "string", enum = ["APPROVAL_ENTRY", "APPROVAL_EXIT", "APPROVAL_ADJUSTMENT", "DIVERGENCE_RESOLUTION", "DOCUMENT_REVIEW", "QUALITY_CHECK"] }
          priority    = { type = "string", enum = ["LOW", "MEDIUM", "HIGH", "URGENT"] }
          assignee_id = { type = "string" }
          limit       = { type = "integer", default = 50 }
        }
      }
    },
    {
      name        = "sga_create_movement"
      description = "Cria uma nova movimentação de estoque"
      input_schema = {
        type     = "object"
        required = ["movement_type", "part_number", "quantity"]
        properties = {
          movement_type           = { type = "string", enum = ["ENTRADA", "SAIDA", "TRANSFERENCIA", "RESERVA", "LIBERACAO", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"] }
          part_number             = { type = "string" }
          quantity                = { type = "integer", minimum = 1 }
          source_location_id      = { type = "string", description = "Local de origem (para saída/transferência)" }
          destination_location_id = { type = "string", description = "Local de destino (para entrada/transferência)" }
          project_id              = { type = "string" }
          serial_numbers          = { type = "array", items = { type = "string" }, description = "Lista de serial numbers" }
          nf_number               = { type = "string" }
          nf_date                 = { type = "string", format = "date" }
          reason                  = { type = "string" }
        }
      }
    },
    {
      name        = "sga_reconcile_sap"
      description = "Compara estoque SGA com dados exportados do SAP"
      input_schema = {
        type     = "object"
        required = ["sap_data"]
        properties = {
          sap_data = {
            type = "array"
            items = {
              type     = "object"
              required = ["part_number", "quantity"]
              properties = {
                part_number   = { type = "string" }
                quantity      = { type = "integer" }
                location_code = { type = "string" }
                project_code  = { type = "string" }
              }
            }
            description = "Lista de itens do SAP para reconciliação"
          }
          include_serials = { type = "boolean", default = false }
        }
      }
    },
    # =============================================================================
    # Schema Introspection Tools (for NEXO Import schema-aware validation)
    # Added January 2026 - Issue #17: SigV4 Auth + Schema Tools
    # =============================================================================
    {
      name        = "sga_get_schema_metadata"
      description = "Obtém metadados completos do schema PostgreSQL para validação de importação NEXO"
      input_schema = {
        type        = "object"
        properties  = {}
        description = "Retorna tabelas, colunas, ENUMs, FKs e constraints do schema SGA"
      }
    },
    {
      name        = "sga_get_table_columns"
      description = "Obtém metadados das colunas de uma tabela específica"
      input_schema = {
        type     = "object"
        required = ["table_name"]
        properties = {
          table_name  = { type = "string", description = "Nome da tabela PostgreSQL" }
          schema_name = { type = "string", default = "sga", description = "Schema PostgreSQL (default: sga)" }
        }
      }
    },
    {
      name        = "sga_get_enum_values"
      description = "Obtém valores válidos de um ENUM PostgreSQL"
      input_schema = {
        type     = "object"
        required = ["enum_name"]
        properties = {
          enum_name = { type = "string", description = "Nome do tipo ENUM PostgreSQL" }
        }
      }
    }
  ]
}

# =============================================================================
# SSM Parameters for Gateway Configuration
# =============================================================================
# Store gateway configuration for reference by other resources

resource "aws_ssm_parameter" "sga_gateway_config" {
  name        = "/${var.project_name}/sga/gateway/config"
  description = "AgentCore Gateway configuration for SGA"
  type        = "String"
  value       = jsonencode(local.sga_gateway_config)

  tags = {
    Name        = "${local.name_prefix}-sga-gateway-config"
    Module      = "SGA"
    Feature     = "AgentCore Gateway"
    Description = "Gateway configuration stored for reference"
  }
}

resource "aws_ssm_parameter" "sga_gateway_tools" {
  name        = "/${var.project_name}/sga/gateway/tools"
  description = "MCP tool definitions for SGA Gateway"
  type        = "String"
  tier        = "Advanced"
  value       = jsonencode(local.sga_mcp_tools)

  tags = {
    Name        = "${local.name_prefix}-sga-gateway-tools"
    Module      = "SGA"
    Feature     = "AgentCore Gateway"
    Description = "Tool schema definitions for Gateway"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_gateway_role_arn" {
  description = "IAM role ARN for AgentCore Gateway"
  value       = aws_iam_role.sga_agentcore_gateway.arn
}

output "sga_gateway_id" {
  description = "AgentCore Gateway ID (created via boto3)"
  value       = local.sga_gateway_id
}

output "sga_gateway_url" {
  description = "AgentCore Gateway MCP endpoint URL"
  value       = local.sga_gateway_url
}

output "sga_gateway_target_id" {
  description = "Lambda target ID for SGAPostgresTools"
  value       = local.sga_target_id
}

output "sga_gateway_config_ssm" {
  description = "SSM parameter path for Gateway configuration"
  value       = aws_ssm_parameter.sga_gateway_config.name
}

output "sga_gateway_tools_ssm" {
  description = "SSM parameter path for Gateway tools schema"
  value       = aws_ssm_parameter.sga_gateway_tools.name
}

output "tavily_target_name" {
  description = "Tavily Gateway target name"
  value       = local.tavily_target_name
}

# =============================================================================
# AWS CLI Commands for Gateway Creation
# =============================================================================
# Run these commands after Terraform apply to create the Gateway:
#
# 1. Create Gateway:
# aws bedrock-agentcore create-gateway \
#   --name "faiston-one-sga-gateway-prod" \
#   --role-arn "$(terraform output -raw sga_gateway_role_arn)" \
#   --authorization-configuration "$(aws ssm get-parameter --name /faiston-one/sga/gateway/config --query 'Parameter.Value' --output text | jq -r '.authorization_configuration')" \
#   --semantic-search-configuration '{"semanticSearchEnabled": true}'
#
# 2. Create Lambda Target:
# aws bedrock-agentcore create-gateway-target \
#   --gateway-identifier "<GATEWAY_ID_FROM_STEP_1>" \
#   --name "SGAPostgresTools" \
#   --description "SGA Inventory PostgreSQL tools via Lambda" \
#   --target-configuration '{
#     "mcp": {
#       "lambda": {
#         "lambdaArn": "$(terraform output -raw sga_postgres_tools_lambda_arn)",
#         "toolSchema": {
#           "inlinePayload": '"$(aws ssm get-parameter --name /faiston-one/sga/gateway/tools --query 'Parameter.Value' --output text)"'
#         }
#       }
#     }
#   }' \
#   --credential-provider-configurations '[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]'
#
# 3. Store Gateway URL in SSM:
# GATEWAY_URL=$(aws bedrock-agentcore get-gateway --gateway-identifier <GATEWAY_ID> --query 'gateway.endpoint' --output text)
# aws ssm put-parameter --name /faiston-one/sga/gateway/url --value "$GATEWAY_URL" --type String --overwrite
#
# =============================================================================
# 4. Create Tavily Target (Equipment Enrichment):
# =============================================================================
# NOTE: Tavily is available as native AgentCore Gateway integration.
# Reference: https://aws.amazon.com/blogs/opensource/tavily-available-aws-bedrock-agentcore-gateway/
#
# aws bedrock-agentcore create-gateway-target \
#   --gateway-identifier "faiston-one-sga-gateway-prod-qbnlm3ao63" \
#   --name "TavilySearchMCP" \
#   --description "Tavily AI-optimized search for equipment specs and documentation" \
#   --target-configuration '{
#     "openApi": {
#       "openApiSchemaUrl": "https://api.tavily.com/.well-known/openapi.json",
#       "authenticationScheme": {
#         "apiKey": {
#           "headerName": "api-key",
#           "secretArn": "'"$(terraform output -raw tavily_secret_arn)"'"
#         }
#       }
#     }
#   }' \
#   --credential-provider-configurations '[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]' \
#   --profile faiston-aio
#
# After creation, update local.tavily_target_id with the returned target ID.
#
# =============================================================================
# 5. Verify Tavily Target:
# =============================================================================
# aws bedrock-agentcore list-gateway-targets \
#   --gateway-identifier "faiston-one-sga-gateway-prod-qbnlm3ao63" \
#   --profile faiston-aio
#
# Test Tavily via Gateway MCP:
# curl -X POST "https://faiston-one-sga-gateway-prod-qbnlm3ao63.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp" \
#   -H "Content-Type: application/json" \
#   --aws-sigv4 "aws:amz:us-east-2:bedrock-agentcore" \
#   -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"tavily_search","arguments":{"query":"Cisco C9200-24P specifications"}},"id":1}'
# =============================================================================
