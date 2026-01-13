# =============================================================================
# AgentCore Runtimes for SGA Inventory - 14 Separate Agents
# =============================================================================
# Each agent runs in its own dedicated AgentCore Runtime for:
# - Independent scaling and lifecycle
# - Cross-agent communication via A2A protocol (JSON-RPC 2.0, SigV4 signed)
#
# Architecture (100% Agentic - AWS Strands Agents + AWS Bedrock AgentCore):
# - 14 runtimes (one per agent)
# - A2A protocol (port 9000, root path /) - uses Strands A2AServer
# - AgentCore Memory (global namespace)
# - AgentCore Identity for cross-agent auth
#
# MIGRATION COMPLETE: BedrockAgentCoreApp (HTTP) → Strands A2AServer (A2A)
# - Old: HTTP protocol, port 8080, /invocations endpoint
# - New: A2A protocol, port 9000, root path /
#
# Reference: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
# Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html
# =============================================================================

# =============================================================================
# Data Sources - External Configuration
# =============================================================================

# Google API Key for Gemini 3.0 (Google ADK)
# The resource is defined in ssm_academy.tf with value managed outside Terraform.
# We use a data source to read the actual decrypted value at plan/apply time.
data "aws_ssm_parameter" "google_api_key" {
  name            = aws_ssm_parameter.academy_google_api_key.name
  with_decryption = true
}

# =============================================================================
# Local Variables - Agent Definitions
# =============================================================================

locals {
  # All 14 SGA agents with their configurations
  sga_agents = {
    # ==========================================================================
    # Core Agents (Orchestration & Memory)
    # ==========================================================================
    nexo_import = {
      name            = "NexoImportAgent"
      description     = "Main orchestrator for intelligent file import with ReAct pattern"
      entry_point     = ["main.py"]
      memory_access   = true
      is_orchestrator = true
      skills = [
        "analyze_file",
        "generate_questions",
        "execute_import",
        "delegate_to_agents"
      ]
    }

    learning = {
      name            = "LearningAgent"
      description     = "Episodic memory agent for import intelligence and pattern learning"
      entry_point     = ["main.py"]
      memory_access   = true
      is_orchestrator = false
      skills = [
        "retrieve_prior_knowledge",
        "create_episode",
        "generate_reflection",
        "compile_memory"
      ]
    }

    validation = {
      name            = "ValidationAgent"
      description     = "Schema validation and data quality agent"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "validate_schema",
        "validate_data",
        "check_constraints",
        "report_errors"
      ]
    }

    schema_evolution = {
      name            = "SchemaEvolutionAgent"
      description     = "Dynamic schema evolution and column creation agent"
      entry_point     = ["main.py"]
      memory_access   = true
      is_orchestrator = false
      skills = [
        "propose_column",
        "create_column",
        "migrate_schema",
        "validate_evolution"
      ]
    }

    # ==========================================================================
    # Import & Intake Agents
    # ==========================================================================
    intake = {
      name            = "IntakeAgent"
      description     = "Nota Fiscal reader and XML/PDF parser"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "read_nf_xml",
        "read_nf_pdf",
        "extract_items",
        "validate_nf"
      ]
    }

    import = {
      name            = "ImportAgent"
      description     = "Bulk import agent for spreadsheets and CSV files"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "parse_csv",
        "parse_xlsx",
        "map_columns",
        "batch_insert"
      ]
    }

    # ==========================================================================
    # Control & Validation Agents
    # ==========================================================================
    estoque_control = {
      name            = "EstoqueControlAgent"
      description     = "Inventory control and stock balance management"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "check_balance",
        "reserve_stock",
        "release_stock",
        "adjust_inventory"
      ]
    }

    compliance = {
      name            = "ComplianceAgent"
      description     = "Regulatory compliance and audit trail agent"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "validate_compliance",
        "generate_audit_report",
        "check_regulations"
      ]
    }

    reconciliacao = {
      name            = "ReconciliacaoAgent"
      description     = "SAP reconciliation and data comparison agent"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "compare_sap_data",
        "identify_divergences",
        "propose_corrections"
      ]
    }

    # ==========================================================================
    # Logistics & Movement Agents
    # ==========================================================================
    expedition = {
      name            = "ExpeditionAgent"
      description     = "Shipment and expedition management agent"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "create_shipment",
        "validate_expedition",
        "generate_documents"
      ]
    }

    carrier = {
      name            = "CarrierAgent"
      description     = "Carrier management and tracking agent"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "select_carrier",
        "track_shipment",
        "calculate_freight"
      ]
    }

    reverse = {
      name            = "ReverseAgent"
      description     = "Reverse logistics and returns management"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "process_return",
        "validate_return",
        "update_inventory"
      ]
    }

    # ==========================================================================
    # Support & Research Agents
    # ==========================================================================
    observation = {
      name            = "ObservationAgent"
      description     = "Monitoring and alerting agent"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "monitor_inventory",
        "detect_anomalies",
        "send_alerts"
      ]
    }

    equipment_research = {
      name            = "EquipmentResearchAgent"
      description     = "Equipment research and knowledge base agent"
      entry_point     = ["main.py"]
      memory_access   = false
      is_orchestrator = false
      skills = [
        "search_equipment_kb",
        "get_specifications",
        "suggest_alternatives"
      ]
    }
  }

  # S3 bucket and prefix for agent code artifacts
  sga_agents_code_bucket = aws_s3_bucket.sga_documents.id
  sga_agents_code_prefix = "agentcore/agents"

  # Environment variables common to all agents
  sga_common_env_vars = {
    # AWS Configuration
    AWS_REGION = var.aws_region

    # AgentCore Memory (GLOBAL namespace)
    AGENTCORE_MEMORY_ID        = "nexo_sga_learning_memory-u3ypElEdl1"
    AGENTCORE_MEMORY_NAMESPACE = "/strategy/import/company"

    # AgentCore Gateway
    AGENTCORE_GATEWAY_URL = local.sga_gateway_url

    # DynamoDB Tables
    INVENTORY_TABLE = aws_dynamodb_table.sga_inventory.name
    HIL_TASKS_TABLE = aws_dynamodb_table.sga_hil_tasks.name
    AUDIT_LOG_TABLE = aws_dynamodb_table.sga_audit_log.name
    SESSIONS_TABLE  = aws_dynamodb_table.sga_sessions.name

    # S3 Buckets
    DOCUMENTS_BUCKET = aws_s3_bucket.sga_documents.id

    # PostgreSQL via RDS Proxy
    RDS_PROXY_ENDPOINT = aws_db_proxy.sga.endpoint
    RDS_DATABASE_NAME  = "sga_inventory"
    RDS_PORT           = "5432"
    RDS_SECRET_ARN     = aws_secretsmanager_secret.sga_rds_master.arn

    # Logging
    LOG_LEVEL = var.environment == "prod" ? "INFO" : "DEBUG"

    # Google ADK Configuration (Gemini 3.0 Pro)
    # Required for Google ADK agents to authenticate with Gemini API
    GOOGLE_API_KEY = data.aws_ssm_parameter.google_api_key.value
  }
}

# =============================================================================
# S3 Objects for Agent Code Artifacts
# =============================================================================
# Each agent's code is deployed as a ZIP file to S3
# GitHub Actions will upload these during deployment

# Note: The actual ZIP files are created and uploaded by GitHub Actions
# This placeholder resource ensures Terraform knows about the expected structure

# =============================================================================
# AgentCore Runtimes - One per Agent
# =============================================================================

resource "aws_bedrockagentcore_agent_runtime" "sga_agents" {
  for_each = local.sga_agents

  # AgentCore requires: ^[a-zA-Z][a-zA-Z0-9_]{0,47}$ (no hyphens allowed)
  agent_runtime_name = "faiston_sga_${each.key}"
  description        = each.value.description
  role_arn           = aws_iam_role.sga_agentcore_execution.arn

  # Code artifact from S3 (Python 3.13, ARM64)
  agent_runtime_artifact {
    code_configuration {
      entry_point = each.value.entry_point
      runtime     = "PYTHON_3_13"

      code {
        s3 {
          bucket = local.sga_agents_code_bucket
          prefix = "${local.sga_agents_code_prefix}/${each.key}/agent.zip"
        }
      }
    }
  }

  # Network configuration (PUBLIC for cross-agent communication)
  network_configuration {
    network_mode = "PUBLIC"
  }

  # A2A Protocol configuration (JSON-RPC 2.0, port 9000 → /)
  # MIGRATION: Strands A2AServer now serves at root path /
  # Reference: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
  protocol_configuration {
    server_protocol = "A2A"
  }

  # Environment variables for the agent
  environment_variables = merge(
    local.sga_common_env_vars,
    {
      # Agent-specific configuration
      AGENT_ID          = each.key
      AGENT_NAME        = each.value.name
      IS_ORCHESTRATOR   = tostring(each.value.is_orchestrator)
      HAS_MEMORY_ACCESS = tostring(each.value.memory_access)

      # A2A URLs for other agents (populated by SSM lookup at runtime)
      # Format: AGENT_URL_{AGENT_ID} = https://...
    }
  )

  # Lifecycle configuration
  lifecycle_configuration {
    idle_runtime_session_timeout = 300  # 5 minutes
    max_lifetime                 = 3600 # 1 hour
  }

  tags = merge(local.common_tags, {
    Name         = "${local.name_prefix}-sga-${each.key}"
    Module       = "SGA"
    Feature      = "AgentCore Runtime"
    AgentID      = each.key
    AgentName    = each.value.name
    Orchestrator = each.value.is_orchestrator ? "true" : "false"
  })
}

# =============================================================================
# AgentCore Runtime Endpoints - One per Agent Runtime
# =============================================================================
# Each runtime needs a DEFAULT endpoint to be invokable.
# Endpoints provide the entry point for external invocations.
#
# Key concepts:
# - Runtimes are containers/code that run agent logic
# - Endpoints are the "doors" that allow invocations to reach runtimes
# - DEFAULT endpoint points to latest runtime version
#
# Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agent-runtime-versioning.html

resource "aws_bedrockagentcore_agent_runtime_endpoint" "sga_agents" {
  for_each = local.sga_agents

  name             = "DEFAULT"
  agent_runtime_id = aws_bedrockagentcore_agent_runtime.sga_agents[each.key].agent_runtime_id
  description      = "Default endpoint for ${each.value.name}"

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-sga-${each.key}-endpoint"
    Module    = "SGA"
    Feature   = "AgentCore Runtime Endpoint"
    AgentID   = each.key
    AgentName = each.value.name
  })

  # DEFAULT endpoints are auto-managed by AgentCore and cannot be updated
  # via UpdateAgentRuntimeEndpoint API. Ignore all changes after import.
  lifecycle {
    ignore_changes = all
  }
}

# =============================================================================
# Outputs
# =============================================================================
# NOTE: SSM Parameters for Agent Discovery have been REMOVED (100% A2A Architecture)
# Agent runtime IDs are now hardcoded in server/agentcore-inventory/shared/a2a_client.py
# This eliminates SSM latency (~50ms per lookup) and simplifies the architecture.

output "sga_agent_runtime_ids" {
  description = "Map of agent IDs to their AgentCore Runtime IDs"
  value = {
    for agent_id, runtime in aws_bedrockagentcore_agent_runtime.sga_agents :
    agent_id => runtime.agent_runtime_id
  }
}

output "sga_agent_runtime_arns" {
  description = "Map of agent IDs to their AgentCore Runtime ARNs"
  value = {
    for agent_id, runtime in aws_bedrockagentcore_agent_runtime.sga_agents :
    agent_id => runtime.agent_runtime_arn
  }
}

output "sga_agent_endpoint_arns" {
  description = "Map of agent IDs to their AgentCore Runtime Endpoint ARNs"
  value = {
    for agent_id, endpoint in aws_bedrockagentcore_agent_runtime_endpoint.sga_agents :
    agent_id => endpoint.agent_runtime_endpoint_arn
  }
}

# NOTE: sga_agent_urls and sga_agent_registry_ssm outputs REMOVED (100% A2A Architecture)
# Runtime IDs are now hardcoded in a2a_client.py - no SSM parameters needed
