# =============================================================================
# SchemaEvolutionAgent - AgentCore Runtime Entry Point
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# This agent manages dynamic PostgreSQL schema evolution:
# - Create columns via MCP Gateway (NEVER direct DB connections!)
# - Validate column requests against security rules
# - Infer PostgreSQL types from sample data
# - Recommend JSONB metadata fallback when lock timeout
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
# - Database: MCP Gateway → Lambda → Aurora PostgreSQL
# - Tracing: X-Ray distributed tracing for observability
#
# Reference:
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
# =============================================================================

import asyncio
import os
import json
import logging
from typing import Dict, Any, Optional

# AgentCore Runtime
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Google ADK
from google.adk.runners import Runner

# Shared infrastructure
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import init_xray_tracing, trace_subsegment
from shared.identity_utils import extract_user_identity, log_identity_context

# Agent definition
from agents.schema_evolution.agent import create_schema_evolution_agent, AGENT_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

APP_NAME = "sga_inventory"
AGENT_NAME = "SchemaEvolutionAgent"


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
        _adk_agent = create_schema_evolution_agent()
        logger.info(f"[{AGENT_NAME}] ADK Agent initialized")
    return _adk_agent


def _get_session_service():
    """Lazy-load Session Service (InMemory - no persistent state needed)."""
    global _session_service
    if _session_service is None:
        from google.adk.sessions import InMemorySessionService
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
    1. Another agent invokes this agent via A2A protocol
    2. The AgentCore Gateway routes a request to this agent

    Args:
        payload: A2A message payload with action and parameters
        context: AgentCore context (session_id, identity, etc.)

    Returns:
        A2A response with result
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Async agent invocation with ADK Runner.

    Implements the 100% Agentic pattern:
    1. Parse A2A message
    2. Emit audit events for Agent Room visibility
    3. Run ADK agent with session
    4. Return A2A response

    Args:
        payload: Parsed payload from A2A message
        context: AgentCore runtime context

    Returns:
        Response dict for A2A protocol
    """
    session_id = getattr(context, "session_id", None) or "default"
    action = payload.get("action", "create_column")

    # Extract user identity from AgentCore context (JWT validated) or payload (fallback)
    # COMPLIANCE: AgentCore Identity v1.0
    user = extract_user_identity(context, payload)
    user_id = user.user_id

    # Log identity context for security monitoring
    log_identity_context(user, AGENT_NAME, action, session_id)

    # Emit START event for Agent Room
    audit.started(
        message=f"Iniciando ação: {action}",
        session_id=session_id,
    )

    try:
        with trace_subsegment("agent_invocation", {"action": action}):
            # Get ADK agent and session service
            adk_agent = _get_adk_agent()
            session_service = _get_session_service()

            # Build message for ADK runner
            message = _build_message(payload)

            # Emit WORKING event
            audit.working(
                message=f"Processando: {action}",
                session_id=session_id,
                details={"payload_keys": list(payload.keys())},
            )

            # Run ADK agent
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

            # Parse response (expect JSON)
            try:
                result = json.loads(response_text) if response_text else {}
            except json.JSONDecodeError:
                result = {"response": response_text}

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

        # Emit ERROR event
        audit.error(
            message=f"Erro ao processar: {action}",
            session_id=session_id,
            error=str(e),
        )

        return {
            "success": False,
            "action": action,
            "error": str(e),
            "agent_id": AGENT_ID,
            "use_metadata_fallback": True,  # Recommend fallback on error
        }


def _build_message(payload: Dict[str, Any]) -> str:
    """
    Build message for ADK runner from A2A payload.

    Args:
        payload: A2A payload

    Returns:
        Natural language message for ADK agent
    """
    action = payload.get("action", "create_column")

    if action == "create_column":
        return f"""Create a new PostgreSQL column with the following parameters:
- Table: {payload.get('table_name', 'pending_entry_items')}
- Column Name: {payload.get('column_name', 'unknown')}
- Column Type: {payload.get('column_type', 'TEXT')}
- Requested By: {payload.get('requested_by', 'system')}
- Original CSV Column: {payload.get('original_csv_column', 'unknown')}
- Sample Values: {json.dumps(payload.get('sample_values', [])[:5])}

Validate the request, sanitize the column name, and create the column via MCP Gateway.
If lock timeout occurs, recommend JSONB metadata fallback."""

    elif action == "validate_column_request":
        return f"""Validate this column creation request:
- Table: {payload.get('table_name', 'pending_entry_items')}
- Column Name: {payload.get('column_name', 'unknown')}
- Column Type: {payload.get('column_type', 'TEXT')}

Check against table whitelist, type whitelist, and SQL injection patterns."""

    elif action == "infer_column_type":
        return f"""Infer the PostgreSQL type for these sample values:
- Sample Values: {json.dumps(payload.get('sample_values', []))}

Return the most appropriate PostgreSQL type from the allowed types list."""

    else:
        return f"Process the following schema evolution request: {json.dumps(payload)}"


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    # Run the AgentCore app
    # Port 9000 is MANDATORY for A2A protocol
    app.run(host="0.0.0.0", port=9000)
