# =============================================================================
# ValidationAgent - AgentCore Runtime Entry Point
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# Validates data and mappings against PostgreSQL schema.
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
# - Role: Called by NexoImportAgent before import execution
#
# Reference:
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
# =============================================================================

import asyncio
import os
import json
import logging
from typing import Dict, Any

# AgentCore Runtime
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Google ADK
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Shared infrastructure
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import init_xray_tracing, trace_subsegment
from shared.identity_utils import extract_user_identity, log_identity_context

# Agent definition
from agents.validation.agent import create_validation_agent, AGENT_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

APP_NAME = "sga_inventory"
AGENT_NAME = "ValidationAgent"


# =============================================================================
# AgentCore App Setup
# =============================================================================

app = BedrockAgentCoreApp()

# Initialize X-Ray tracing
init_xray_tracing(service_name=f"sga-{AGENT_ID}")

# Initialize audit emitter for Agent Room visibility
audit = AgentAuditEmitter(agent_id=AGENT_ID)

# Lazy-loaded components
_adk_agent = None
_session_service = None


def _get_adk_agent():
    """Lazy-load Google ADK Agent."""
    global _adk_agent
    if _adk_agent is None:
        _adk_agent = create_validation_agent()
        logger.info(f"[{AGENT_NAME}] ADK Agent initialized")
    return _adk_agent


def _get_session_service():
    """Lazy-load Session Service (stateless - InMemory)."""
    global _session_service
    if _session_service is None:
        _session_service = InMemorySessionService()
        logger.info(f"[{AGENT_NAME}] InMemory SessionService initialized")
    return _session_service


# =============================================================================
# A2A Protocol Entry Point
# =============================================================================

@app.entrypoint
def agent_invocation(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Entry point for AgentCore Runtime invocations.

    This is called when:
    1. NexoImportAgent calls this agent via A2A protocol
    2. Any other agent requests validation

    Args:
        payload: A2A message payload with action and parameters
        context: AgentCore context (session_id, identity, etc.)

    Returns:
        A2A response with validation result
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Async agent invocation with validation logic.

    Args:
        payload: Parsed payload from A2A message
        context: AgentCore runtime context

    Returns:
        Response dict for A2A protocol
    """
    session_id = getattr(context, "session_id", None) or "default"
    action = payload.get("action", "validate")

    # Extract user identity from AgentCore context (JWT validated) or payload (fallback)
    # COMPLIANCE: AgentCore Identity v1.0
    user = extract_user_identity(context, payload)
    user_id = user.user_id

    # Log identity context for security monitoring
    log_identity_context(user, AGENT_NAME, action, session_id)

    # Emit START event for Agent Room
    audit.started(
        message=f"Iniciando: {action}",
        session_id=session_id,
    )

    try:
        with trace_subsegment("validation_invocation", {"action": action}):
            # Route to appropriate handler based on action
            if action == "validate_mappings":
                result = await _handle_validate_mappings(payload, session_id)
            elif action == "validate_data":
                result = await _handle_validate_data(payload, session_id)
            elif action == "check_constraints":
                result = await _handle_check_constraints(payload, session_id)
            elif action == "validate_schema":
                result = await _handle_validate_schema(payload, session_id)
            else:
                # Generic ADK agent invocation
                result = await _invoke_adk_agent(payload, session_id, user_id)

            # Emit COMPLETED event
            audit.completed(
                message=f"Concluído: {action}",
                session_id=session_id,
                details={"success": result.get("success", True)},
            )

            return {
                "success": result.get("success", True),
                "action": action,
                "result": result,
                "agent_id": AGENT_ID,
            }

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] Error: {e}", exc_info=True)

        audit.error(
            message=f"Erro: {action}",
            session_id=session_id,
            error=str(e),
        )

        return {
            "success": False,
            "action": action,
            "error": str(e),
            "agent_id": AGENT_ID,
        }


# =============================================================================
# Action Handlers
# =============================================================================

async def _handle_validate_mappings(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """
    Validate column mappings against schema.

    Checks:
    1. Target fields exist in schema
    2. No duplicate mappings
    3. Required fields present
    """
    audit.working(
        message="Validando mapeamentos de colunas...",
        session_id=session_id,
    )

    from agents.validation.tools.validate_schema import validate_schema_tool

    column_mappings = payload.get("column_mappings", {})
    target_table = payload.get("target_table", "pending_entry_items")

    result = await validate_schema_tool(
        column_mappings=column_mappings,
        target_table=target_table,
        session_id=session_id,
    )

    return result


async def _handle_validate_data(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """
    Validate data rows against schema constraints.

    Checks:
    1. Data types match schema
    2. Required fields have values
    3. Value constraints (length, format)
    """
    audit.working(
        message="Validando dados...",
        session_id=session_id,
    )

    from agents.validation.tools.validate_data import validate_data_tool

    rows = payload.get("rows", [])
    column_mappings = payload.get("column_mappings", {})
    target_table = payload.get("target_table", "pending_entry_items")

    result = await validate_data_tool(
        rows=rows,
        column_mappings=column_mappings,
        target_table=target_table,
        session_id=session_id,
    )

    return result


async def _handle_check_constraints(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """
    Check database constraints for import data.

    Checks:
    1. Foreign key references
    2. Unique constraints
    3. Check constraints
    """
    audit.working(
        message="Verificando restrições do banco...",
        session_id=session_id,
    )

    from agents.validation.tools.check_constraints import check_constraints_tool

    rows = payload.get("rows", [])
    target_table = payload.get("target_table", "pending_entry_items")

    result = await check_constraints_tool(
        rows=rows,
        target_table=target_table,
        session_id=session_id,
    )

    return result


async def _handle_validate_schema(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """
    Validate that target table and columns exist.

    Used by SchemaEvolutionAgent before creating new columns.
    """
    audit.working(
        message="Validando schema do banco...",
        session_id=session_id,
    )

    from agents.validation.tools.validate_schema import validate_schema_tool

    target_table = payload.get("target_table", "pending_entry_items")
    columns = payload.get("columns", [])

    result = await validate_schema_tool(
        column_mappings={c: c for c in columns},
        target_table=target_table,
        session_id=session_id,
    )

    return result


# =============================================================================
# Helper Functions
# =============================================================================

async def _invoke_adk_agent(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Invoke the ADK agent for generic processing."""
    adk_agent = _get_adk_agent()
    session_service = _get_session_service()

    message = _build_message(payload)

    runner = Runner(
        agent=adk_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    response_text += part.text

    try:
        return json.loads(response_text) if response_text else {}
    except json.JSONDecodeError:
        return {"response": response_text}


def _build_message(payload: Dict[str, Any]) -> str:
    """Build message for ADK runner from payload."""
    action = payload.get("action", "validate")

    if action == "validate_mappings":
        return f"""Validate these column mappings against the schema:

Column Mappings: {json.dumps(payload.get('column_mappings', {}))}
Target Table: {payload.get('target_table', 'pending_entry_items')}

Check for:
1. Invalid field names
2. Duplicate mappings
3. Missing required fields"""

    elif action == "validate_data":
        return f"""Validate this data against schema constraints:

Rows (sample): {json.dumps(payload.get('rows', [])[:5])}
Column Mappings: {json.dumps(payload.get('column_mappings', {}))}

Check data types, required fields, and value constraints."""

    return f"Validate: {json.dumps(payload)}"


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
