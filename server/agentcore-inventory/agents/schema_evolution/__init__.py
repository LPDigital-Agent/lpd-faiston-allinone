# =============================================================================
# SchemaEvolutionAgent - Module Exports
# =============================================================================
# Dynamic PostgreSQL column creation agent.
#
# Architecture: 100% Agentic (Google ADK + AWS Bedrock AgentCore)
# Protocol: A2A (JSON-RPC 2.0)
#
# Usage:
#   # From other agents via A2A protocol:
#   from shared.a2a_client import delegate_to_schema_evolution
#   result = await delegate_to_schema_evolution({
#       "action": "create_column",
#       "table_name": "pending_entry_items",
#       "column_name": "serial_number",
#       "column_type": "VARCHAR(100)",
#       "requested_by": "user123"
#   })
# =============================================================================

from agents.schema_evolution.agent import (
    create_schema_evolution_agent,
    AGENT_ID,
    AGENT_NAME,
)

__all__ = [
    "create_schema_evolution_agent",
    "AGENT_ID",
    "AGENT_NAME",
]
