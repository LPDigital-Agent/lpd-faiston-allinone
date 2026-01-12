# =============================================================================
# ImportAgent - AgentCore Runtime Entry Point
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# Handles bulk importing inventory data from CSV/Excel files:
# - Parse CSV/Excel with auto-column detection
# - AI-assisted part number matching
# - Validation and preview before import
# - Batch movement creation
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
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
from shared.a2a_client import delegate_to_learning, delegate_to_validation
from shared.xray_tracer import init_xray_tracing, trace_subsegment, trace_a2a_call
from shared.identity_utils import extract_user_identity, log_identity_context

# Agent definition
from agents.import.agent import create_import_agent, AGENT_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

APP_NAME = "sga_inventory"
AGENT_NAME = "ImportAgent"


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
        _adk_agent = create_import_agent()
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

    Args:
        payload: A2A message payload with action and parameters
        context: AgentCore context (session_id, identity, etc.)

    Returns:
        A2A response with result
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Async agent invocation with bulk import logic.

    Args:
        payload: Parsed payload from A2A message
        context: AgentCore runtime context

    Returns:
        Response dict for A2A protocol
    """
    session_id = getattr(context, "session_id", None) or "default"
    action = payload.get("action", "process")

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
        with trace_subsegment("import_invocation", {"action": action}):
            # Route to appropriate handler based on action
            if action == "preview_import":
                result = await _handle_preview_import(payload, session_id, user_id)
            elif action == "execute_import":
                result = await _handle_execute_import(payload, session_id, user_id)
            elif action == "validate_mapping":
                result = await _handle_validate_mapping(payload, session_id)
            elif action == "match_rows":
                result = await _handle_match_rows(payload, session_id)
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

async def _handle_preview_import(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Handle import preview request.

    Parses file, detects columns, and matches PNs for preview rows.
    """
    audit.working(
        message="Analisando arquivo para importação...",
        session_id=session_id,
    )

    from agents.import.tools.preview_import import preview_import_tool

    return await preview_import_tool(
        s3_key=payload.get("s3_key"),
        filename=payload.get("filename"),
        project_id=payload.get("project_id"),
        destination_location_id=payload.get("destination_location_id"),
        session_id=session_id,
    )


async def _handle_execute_import(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Handle import execution request.

    Creates movements for all valid rows.
    """
    audit.working(
        message="Executando importação em massa...",
        session_id=session_id,
    )

    from agents.import.tools.execute_import import execute_import_tool

    result = await execute_import_tool(
        import_id=payload.get("import_id"),
        s3_key=payload.get("s3_key"),
        column_mappings=payload.get("column_mappings", []),
        pn_overrides=payload.get("pn_overrides"),
        project_id=payload.get("project_id"),
        destination_location_id=payload.get("destination_location_id"),
        operator_id=user_id,
        session_id=session_id,
    )

    # Store learning episode if successful
    if result.get("success"):
        await _store_learning_episode(
            import_result=result,
            user_id=user_id,
            session_id=session_id,
        )

    return result


async def _handle_validate_mapping(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """
    Handle column mapping validation request.
    """
    audit.working(
        message="Validando mapeamentos de colunas...",
        session_id=session_id,
    )

    # Delegate to ValidationAgent
    response = await delegate_to_validation({
        "action": "validate_mappings",
        "column_mappings": payload.get("column_mappings", {}),
        "target_table": "pending_entry_items",
    }, session_id=session_id)

    return response.response if response.success else {"error": response.error}


async def _handle_match_rows(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """
    Handle row-to-PN matching request.
    """
    audit.working(
        message="Identificando part numbers...",
        session_id=session_id,
    )

    from agents.import.tools.preview_import import match_rows_to_pn

    return await match_rows_to_pn(
        rows=payload.get("rows", []),
        session_id=session_id,
    )


# =============================================================================
# A2A Delegation
# =============================================================================

@trace_a2a_call("learning")
async def _store_learning_episode(
    import_result: Dict[str, Any],
    user_id: str,
    session_id: str,
) -> None:
    """Store learning episode for future imports."""
    audit.delegating(
        target_agent="learning",
        message="Registrando aprendizado de importação...",
        session_id=session_id,
    )

    try:
        await delegate_to_learning({
            "action": "create_episode",
            "user_id": user_id,
            "episode_type": "bulk_import",
            "data": {
                "filename_pattern": import_result.get("filename", ""),
                "column_mappings": import_result.get("column_mappings_used", []),
                "rows_imported": import_result.get("rows_imported", 0),
                "match_rate": import_result.get("match_rate", 0),
            },
        }, session_id=session_id)
    except Exception as e:
        logger.warning(f"[{AGENT_NAME}] Failed to store learning episode: {e}")


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

    message = f"Process import action: {json.dumps(payload)}"

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


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
