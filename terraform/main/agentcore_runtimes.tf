# =============================================================================
# AgentCore Runtimes for SGA Inventory - 14 Separate Agents
# =============================================================================
# Each agent runs in its own dedicated AgentCore Runtime for:
# - Unique A2A identity (Agent Cards)
# - Independent scaling and lifecycle
# - Cross-agent communication via A2A protocol
#
# Architecture (100% Agentic - Google ADK + AWS Bedrock AgentCore):
# - 14 runtimes (one per agent)
# - A2A protocol (JSON-RPC 2.0, port 9000)
# - AgentCore Memory (global namespace)
# - AgentCore Identity for cross-agent auth
#
# Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
# =============================================================================

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
      name        = "NexoImportAgent"
      description = "Main orchestrator for intelligent file import with ReAct pattern"
      entry_point = ["main.py"]
      memory_access = true
      is_orchestrator = true
      skills = [
        "analyze_file",
        "generate_questions",
        "execute_import",
        "delegate_to_agents"
      ]
    }

    learning = {
      name        = "LearningAgent"
      description = "Episodic memory agent for import intelligence and pattern learning"
      entry_point = ["main.py"]
      memory_access = true
      is_orchestrator = false
      skills = [
        "retrieve_prior_knowledge",
        "create_episode",
        "generate_reflection",
        "compile_memory"
      ]
    }

    validation = {
      name        = "ValidationAgent"
      description = "Schema validation and data quality agent"
      entry_point = ["main.py"]
      memory_access = false
      is_orchestrator = false
      skills = [
        "validate_schema",
        "validate_data",
        "check_constraints",
        "report_errors"
      ]
    }

    schema_evolution = {
      name        = "SchemaEvolutionAgent"
      description = "Dynamic schema evolution and column creation agent"
      entry_point = ["main.py"]
      memory_access = true
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
      name        = "IntakeAgent"
      description = "Nota Fiscal reader and XML/PDF parser"
      entry_point = ["main.py"]
      memory_access = false
      is_orchestrator = false
      skills = [
        "read_nf_xml",
        "read_nf_pdf",
        "extract_items",
        "validate_nf"
      ]
    }

    import = {
      name        = "ImportAgent"
      description = "Bulk import agent for spreadsheets and CSV files"
      entry_point = ["main.py"]
      memory_access = false
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
      name        = "EstoqueControlAgent"
      description = "Inventory control and stock balance management"
      entry_point = ["main.py"]
      memory_access = false
      is_orchestrator = false
      skills = [
        "check_balance",
        "reserve_stock",
        "release_stock",
        "adjust_inventory"
      ]
    }

    compliance = {
      name        = "ComplianceAgent"
      description = "Regulatory compliance and audit trail agent"
      entry_point = ["main.py"]
      memory_access = false
      is_orchestrator = false
      skills = [
        "validate_compliance",
        "generate_audit_report",
        "check_regulations"
      ]
    }

    reconciliacao = {
      name        = "ReconciliacaoAgent"
      description = "SAP reconciliation and data comparison agent"
      entry_point = ["main.py"]
      memory_access = false
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
      name        = "ExpeditionAgent"
      description = "Shipment and expedition management agent"
      entry_point = ["main.py"]
      memory_access = false
      is_orchestrator = false
      skills = [
        "create_shipment",
        "validate_expedition",
        "generate_documents"
      ]
    }

    carrier = {
      name        = "CarrierAgent"
      description = "Carrier management and tracking agent"
      entry_point = ["main.py"]
      memory_access = false
      is_orchestrator = false
      skills = [
        "select_carrier",
        "track_shipment",
        "calculate_freight"
      ]
    }

    reverse = {
      name        = "ReverseAgent"
      description = "Reverse logistics and returns management"
      entry_point = ["main.py"]
      memory_access = false
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
      name        = "ObservationAgent"
      description = "Monitoring and alerting agent"
      entry_point = ["main.py"]
      memory_access = false
      is_orchestrator = false
      skills = [
        "monitor_inventory",
        "detect_anomalies",
        "send_alerts"
      ]
    }

    equipment_research = {
      name        = "EquipmentResearchAgent"
      description = "Equipment research and knowledge base agent"
      entry_point = ["main.py"]
      memory_access = false
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
    AGENTCORE_MEMORY_ID        = "nexo_agent_mem-Z5uQr8CDGf"
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

  # Network configuration (PUBLIC for A2A communication)
  network_configuration {
    network_mode = "PUBLIC"
  }

  # A2A Protocol configuration (JSON-RPC 2.0, port 9000)
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
    Name        = "${local.name_prefix}-sga-${each.key}"
    Module      = "SGA"
    Feature     = "AgentCore Runtime"
    AgentID     = each.key
    AgentName   = each.value.name
    Orchestrator = each.value.is_orchestrator ? "true" : "false"
  })
}

# =============================================================================
# SSM Parameters for Agent Discovery (Agent Cards)
# =============================================================================
# Store runtime URLs for A2A discovery

resource "aws_ssm_parameter" "sga_agent_urls" {
  for_each = local.sga_agents

  name        = "/${var.project_name}/sga/agents/${each.key}/url"
  description = "AgentCore Runtime URL for ${each.value.name}"
  type        = "String"
  # FIX: Use full ARN (URL-encoded) instead of runtime ID - required by InvokeAgentRuntime API
  value       = "https://bedrock-agentcore.${var.aws_region}.amazonaws.com/runtimes/${urlencode(aws_bedrockagentcore_agent_runtime.sga_agents[each.key].agent_runtime_arn)}/invocations?qualifier=DEFAULT"

  tags = merge(local.common_tags, {
    Name      = "${local.name_prefix}-sga-${each.key}-url"
    Module    = "SGA"
    Feature   = "Agent Discovery"
    AgentID   = each.key
    AgentName = each.value.name
  })
}

# Combined agent registry for runtime lookup
resource "aws_ssm_parameter" "sga_agent_registry" {
  name        = "/${var.project_name}/sga/agents/registry"
  description = "Registry of all SGA agent runtime URLs for A2A discovery"
  type        = "String"
  tier        = "Advanced"
  value = jsonencode({
    for agent_id, agent_config in local.sga_agents : agent_id => {
      name        = agent_config.name
      description = agent_config.description
      # FIX: Use full ARN (URL-encoded) instead of runtime ID - required by InvokeAgentRuntime API
      url         = "https://bedrock-agentcore.${var.aws_region}.amazonaws.com/runtimes/${urlencode(aws_bedrockagentcore_agent_runtime.sga_agents[agent_id].agent_runtime_arn)}/invocations?qualifier=DEFAULT"
      runtime_id  = aws_bedrockagentcore_agent_runtime.sga_agents[agent_id].agent_runtime_id
      runtime_arn = aws_bedrockagentcore_agent_runtime.sga_agents[agent_id].agent_runtime_arn
      skills      = agent_config.skills
      memory_access = agent_config.memory_access
      is_orchestrator = agent_config.is_orchestrator
    }
  })

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-sga-agent-registry"
    Module  = "SGA"
    Feature = "Agent Discovery"
  })
}

# =============================================================================
# Outputs
# =============================================================================

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

output "sga_agent_urls" {
  description = "Map of agent IDs to their invocation URLs"
  sensitive   = true
  value = {
    for agent_id, param in aws_ssm_parameter.sga_agent_urls :
    agent_id => param.value
  }
}

output "sga_agent_registry_ssm" {
  description = "SSM parameter path for agent registry"
  value       = aws_ssm_parameter.sga_agent_registry.name
}
