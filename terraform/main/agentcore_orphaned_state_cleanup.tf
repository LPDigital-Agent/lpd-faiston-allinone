# =============================================================================
# Orphaned State Cleanup - AgentCore Runtime Endpoints
# =============================================================================
# This file uses Terraform 1.7+ `removed` blocks to safely remove orphaned
# resources from state without attempting to destroy them.
#
# Background:
# - Commit 32f4caf renamed agent key from "import" → "data_import"
# - Terraform state still had the old ["import"] key
# - AWS Bedrock AgentCore DEFAULT endpoints cannot be deleted directly
#   (they're removed automatically when the parent agent is deleted)
# - This caused: ConflictException: Default endpoints are removed when you delete the agent
#
# Solution:
# - The `removed` block tells Terraform to forget about the resource
# - `lifecycle { destroy = false }` prevents any destruction attempts
#
# Reference: https://developer.hashicorp.com/terraform/language/resources/syntax#removing-resources
# =============================================================================

# -----------------------------------------------------------------------------
# Remove orphaned sga_agents["import"] endpoint from state
# -----------------------------------------------------------------------------
# This endpoint was renamed to ["data_import"] but the old key remained in state.
# The `removed` block safely removes it from Terraform management.
removed {
  from = aws_bedrockagentcore_agent_runtime_endpoint.sga_agents["import"]

  lifecycle {
    destroy = false
  }
}
