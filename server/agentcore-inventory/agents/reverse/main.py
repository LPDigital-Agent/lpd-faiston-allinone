# =============================================================================
# ReverseAgent - Main Entry Point
# AWS Bedrock AgentCore Runtime
# =============================================================================
# Agent for handling reverse logistics (devoluções/reversas).
#
# Features:
# - Process return requests
# - Validate original movement (outbound reference)
# - Determine destination depot based on condition
# - Create RETURN movements
# - Handle BAD (defeituoso) items
# =============================================================================

import asyncio
import logging
import os
from typing import Dict, Any

from google.adk.runners import Runner
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import create_reverse_agent, AGENT_ID
from shared.audit_emitter import AgentAuditEmitter
from shared.identity_utils import extract_user_identity, log_identity_context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app and audit
app = BedrockAgentCoreApp()
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@app.entrypoint
def agent_invocation(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Entry point for AgentCore Runtime invocations.

    Handles reverse logistics operations:
    - process_return: Process a return request
    - validate_origin: Validate original exit movement
    - evaluate_condition: AI-assisted condition evaluation
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """Async agent invocation handler."""
    session_id = getattr(context, "session_id", None)

    audit.started(
        "Iniciando operacao de logistica reversa...",
        session_id=session_id,
    )

    try:
        action = payload.get("action", "")

        # Extract user identity from AgentCore context (JWT validated) or payload (fallback)
        # COMPLIANCE: AgentCore Identity v1.0
        user = extract_user_identity(context, payload)
        user_id = user.user_id

        # Log identity context for security monitoring
        log_identity_context(user, AGENT_ID, action, session_id)

        # Route to appropriate handler
        if action == "process_return":
            result = await handle_process_return(payload, session_id)
        elif action == "validate_origin":
            result = await handle_validate_origin(payload, session_id)
        elif action == "evaluate_condition":
            result = await handle_evaluate_condition(payload, session_id)
        else:
            # Use ADK Runner for conversational queries
            result = await run_adk_agent(payload, session_id, user_id)

        audit.completed(
            f"Operacao concluida: {action or 'consulta'}",
            session_id=session_id,
            details={"action": action},
        )

        return result

    except Exception as e:
        logger.error(f"[ReverseAgent] Error: {e}", exc_info=True)
        audit.error(
            "Erro na logistica reversa",
            session_id=session_id,
            error=str(e),
        )
        return {"success": False, "error": str(e)}


async def run_adk_agent(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Run Google ADK agent for conversational queries."""
    from google.adk.sessions import InMemorySessionService

    agent = create_reverse_agent()
    session_service = InMemorySessionService()

    runner = Runner(
        agent=agent,
        app_name="sga_inventory",
        session_service=session_service,
    )

    message = payload.get("message", payload.get("query", ""))
    response = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id or "default",
        new_message=message,
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    response += part.text

    return {"success": True, "response": response}


# =============================================================================
# Action Handlers
# =============================================================================


async def handle_process_return(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle process_return action."""
    from tools.process_return import process_return_tool

    audit.working(
        f"Processando retorno: {payload.get('serial_number')}",
        session_id=session_id,
    )

    return await process_return_tool(
        serial_number=payload.get("serial_number", ""),
        reason=payload.get("reason", ""),
        condition=payload.get("condition", ""),
        origin_reference=payload.get("origin_reference"),
        project_id=payload.get("project_id"),
        notes=payload.get("notes", ""),
        operator_id=payload.get("operator_id", "system"),
        session_id=session_id,
    )


async def handle_validate_origin(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle validate_origin action."""
    from tools.validate_origin import validate_origin_tool

    audit.working(
        f"Validando rastreabilidade: {payload.get('serial_number')}",
        session_id=session_id,
    )

    return await validate_origin_tool(
        serial_number=payload.get("serial_number", ""),
        session_id=session_id,
    )


async def handle_evaluate_condition(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle evaluate_condition action."""
    from tools.evaluate_condition import evaluate_condition_tool

    audit.working(
        f"Avaliando condicao: {payload.get('serial_number')}",
        session_id=session_id,
    )

    return await evaluate_condition_tool(
        serial_number=payload.get("serial_number", ""),
        inspection_notes=payload.get("inspection_notes", ""),
        test_results=payload.get("test_results"),
        session_id=session_id,
    )


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
