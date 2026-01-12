# =============================================================================
# ObservationAgent - Main Entry Point
# AWS Bedrock AgentCore Runtime
# =============================================================================
# AI agent that observes import data and generates intelligent commentary.
# Follows the "Observe → Learn → Act" pattern.
#
# Features:
# - Analyze import data for patterns and anomalies
# - Generate confidence scores
# - Provide actionable suggestions
# - Create insights for memory/learning
# =============================================================================

import asyncio
import logging
import os
from typing import Dict, Any

from google.adk.runners import Runner
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import create_observation_agent, AGENT_ID
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

    Handles observation operations:
    - analyze_import: Generate observations for import data
    - conversational: Free-form queries about import analysis
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """Async agent invocation handler."""
    session_id = getattr(context, "session_id", None)

    audit.started(
        "Iniciando análise de observação...",
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
        if action == "analyze_import":
            result = await handle_analyze_import(payload, session_id)
        else:
            # Use ADK Runner for conversational queries
            result = await run_adk_agent(payload, session_id, user_id)

        audit.completed(
            f"Análise concluída: {action or 'consulta'}",
            session_id=session_id,
            details={"action": action},
        )

        return result

    except Exception as e:
        logger.error(f"[ObservationAgent] Error: {e}", exc_info=True)
        audit.error(
            "Erro na análise de observação",
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

    agent = create_observation_agent()
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


async def handle_analyze_import(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle analyze_import action."""
    from tools.analyze_import import analyze_import_tool

    preview_data = payload.get("preview_data", {})
    context = payload.get("context", {})

    audit.working(
        f"Analisando importação: {preview_data.get('source_type', 'desconhecido')}",
        session_id=session_id,
        details={
            "items_count": preview_data.get("items_count", 0),
            "source_type": preview_data.get("source_type"),
        },
    )

    return await analyze_import_tool(
        preview_data=preview_data,
        context=context,
        session_id=session_id,
    )


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
