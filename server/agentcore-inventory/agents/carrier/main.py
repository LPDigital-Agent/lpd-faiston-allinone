# =============================================================================
# CarrierAgent - Main Entry Point
# AWS Bedrock AgentCore Runtime
# =============================================================================
# Agent for handling shipping carrier selection and quotes.
#
# Features:
# - Get quotes from multiple carriers
# - Recommend best carrier based on cost/urgency
# - Track shipments
# - Generate shipping labels
#
# NOTE: External API integrations are pending for:
# - Correios VIP API
# - Loggi API
# - Gollog/Gol Linhas Aereas API
# =============================================================================

import asyncio
import logging
import os
from typing import Dict, Any

from google.adk.runners import Runner
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import create_carrier_agent, AGENT_ID
from shared.audit_emitter import AgentAuditEmitter

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

    Handles carrier operations:
    - get_quotes: Get quotes from multiple carriers
    - recommend_carrier: Get AI recommendation
    - track_shipment: Track a shipment
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """Async agent invocation handler."""
    session_id = getattr(context, "session_id", None)

    audit.started(
        "Iniciando operacao de transportadora...",
        session_id=session_id,
    )

    try:
        action = payload.get("action", "")
        user_id = payload.get("user_id", "system")

        # Route to appropriate handler
        if action == "get_quotes":
            result = await handle_get_quotes(payload, session_id)
        elif action == "recommend_carrier":
            result = await handle_recommend_carrier(payload, session_id)
        elif action == "track_shipment":
            result = await handle_track_shipment(payload, session_id)
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
        logger.error(f"[CarrierAgent] Error: {e}", exc_info=True)
        audit.error(
            "Erro na operacao de transportadora",
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

    agent = create_carrier_agent()
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


async def handle_get_quotes(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle get_quotes action."""
    from tools.quotes import get_quotes_tool

    audit.working(
        f"Consultando cotacoes de {payload.get('origin_cep')} para {payload.get('destination_cep')}",
        session_id=session_id,
    )

    return await get_quotes_tool(
        origin_cep=payload.get("origin_cep", ""),
        destination_cep=payload.get("destination_cep", ""),
        weight_kg=payload.get("weight_kg", 1.0),
        dimensions=payload.get("dimensions", {}),
        value=payload.get("value", 0.0),
        urgency=payload.get("urgency", "NORMAL"),
        session_id=session_id,
    )


async def handle_recommend_carrier(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle recommend_carrier action."""
    from tools.recommendation import recommend_carrier_tool

    audit.working(
        f"Recomendando transportadora (urgencia: {payload.get('urgency', 'NORMAL')})",
        session_id=session_id,
    )

    return await recommend_carrier_tool(
        urgency=payload.get("urgency", "NORMAL"),
        weight_kg=payload.get("weight_kg", 1.0),
        value=payload.get("value", 0.0),
        destination_state=payload.get("destination_state", "SP"),
        same_city=payload.get("same_city", False),
        session_id=session_id,
    )


async def handle_track_shipment(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle track_shipment action."""
    from tools.tracking import track_shipment_tool

    audit.working(
        f"Rastreando envio: {payload.get('tracking_code')}",
        session_id=session_id,
    )

    return await track_shipment_tool(
        tracking_code=payload.get("tracking_code", ""),
        carrier=payload.get("carrier"),
        session_id=session_id,
    )


# =============================================================================
# Health Check
# =============================================================================


@app.health_check
def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": AGENT_ID,
        "version": "1.0.0",
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port)
