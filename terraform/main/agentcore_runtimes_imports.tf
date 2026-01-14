# =============================================================================
# Terraform Import Blocks for Existing AgentCore Runtime Endpoints
# =============================================================================
# These import blocks bring existing AWS resources into Terraform state.
# The endpoints were auto-created when runtimes were deployed.
#
# After successful import, this file can be removed or kept for documentation.
# Reference: https://developer.hashicorp.com/terraform/language/import
# =============================================================================

# Import existing DEFAULT endpoints for all 14 SGA agent runtimes
# Format: "<runtime_id>,<endpoint_name>" (comma-separated per AWS provider)

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["carrier"]
  id = "faiston_sga_carrier-fVOntdCJaZ,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["compliance"]
  id = "faiston_sga_compliance-2Kty3O64vz,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["equipment_research"]
  id = "faiston_sga_equipment_research-xs7hxg2SfS,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["estoque_control"]
  id = "faiston_sga_estoque_control-jLRAIr8EcI,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["expedition"]
  id = "faiston_sga_expedition-yJ7Nb551hS,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["data_import"]
  id = "faiston_sga_data_import-bPG8FYGk5w,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["intake"]
  id = "faiston_sga_intake-9I7Nwe6ZfP,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["learning"]
  id = "faiston_sga_learning-30cZIOFmzo,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["nexo_import"]
  id = "faiston_sga_nexo_import-0zNtFDAo7M,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["observation"]
  id = "faiston_sga_observation-ACVR2SDmtJ,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["reconciliacao"]
  id = "faiston_sga_reconciliacao-poSPdO6OKm,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["reverse"]
  id = "faiston_sga_reverse-jeiH9k8CbC,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["schema_evolution"]
  id = "faiston_sga_schema_evolution-Ke1i76BvB0,DEFAULT"
}

import {
  to = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["validation"]
  id = "faiston_sga_validation-3zgXMwCxGN,DEFAULT"
}
