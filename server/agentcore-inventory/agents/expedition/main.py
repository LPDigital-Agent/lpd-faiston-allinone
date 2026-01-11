# =============================================================================
# ExpeditionAgent - Main Entry Point
# AWS Bedrock AgentCore Runtime
# =============================================================================
# Agent for handling outbound shipments (expedição/saída).
#
# Features:
# - Process expedition requests from chamados/tickets
# - Verify stock availability
# - Generate SAP-ready data for NF
# - Handle separation and packaging workflow
# - Complete expeditions with tracking info
# =============================================================================

import asyncio
import logging
import os
from typing import Dict, Any

from google.adk.runners import Runner
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import create_expedition_agent, AGENT_ID
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

    Handles expedition operations:
    - process_expedition: Create expedition from chamado
    - verify_stock: Check stock availability
    - generate_sap_data: Generate NF-ready data
    - confirm_separation: Confirm physical separation
    - complete_expedition: Complete with NF/tracking
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """Async agent invocation handler."""
    session_id = getattr(context, "session_id", None)

    audit.started(
        "Iniciando operacao de expedicao...",
        session_id=session_id,
    )

    try:
        action = payload.get("action", "")
        user_id = payload.get("user_id", "system")

        # Route to appropriate handler
        if action == "process_expedition":
            result = await handle_process_expedition(payload, session_id)
        elif action == "verify_stock":
            result = await handle_verify_stock(payload, session_id)
        elif action == "generate_sap_data":
            result = await handle_generate_sap_data(payload, session_id)
        elif action == "confirm_separation":
            result = await handle_confirm_separation(payload, session_id)
        elif action == "complete_expedition":
            result = await handle_complete_expedition(payload, session_id)
        elif action == "get_expedition":
            result = await handle_get_expedition(payload, session_id)
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
        logger.error(f"[ExpeditionAgent] Error: {e}", exc_info=True)
        audit.error(
            "Erro na expedicao",
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

    agent = create_expedition_agent()
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


async def handle_process_expedition(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle process_expedition action."""
    from tools.process_expedition import process_expedition_tool

    audit.working(
        f"Processando expedicao para chamado: {payload.get('chamado_id', 'N/A')}",
        session_id=session_id,
    )

    return await process_expedition_tool(
        chamado_id=payload.get("chamado_id", ""),
        project_id=payload.get("project_id", ""),
        items=payload.get("items", []),
        destination_client=payload.get("destination_client", ""),
        destination_address=payload.get("destination_address", ""),
        urgency=payload.get("urgency", "NORMAL"),
        nature=payload.get("nature", "USO_CONSUMO"),
        notes=payload.get("notes", ""),
        operator_id=payload.get("operator_id", "system"),
        session_id=session_id,
    )


async def handle_verify_stock(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle verify_stock action."""
    from tools.verify_stock import verify_stock_tool

    audit.working(
        f"Verificando estoque: {payload.get('pn_id')}",
        session_id=session_id,
    )

    return await verify_stock_tool(
        pn_id=payload.get("pn_id", ""),
        serial=payload.get("serial"),
        quantity=payload.get("quantity", 1),
        session_id=session_id,
    )


async def handle_generate_sap_data(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle generate_sap_data action."""
    from tools.sap_export import generate_sap_data_tool

    audit.working(
        "Gerando dados SAP para NF...",
        session_id=session_id,
    )

    return await generate_sap_data_tool(
        expedition_id=payload.get("expedition_id", ""),
        session_id=session_id,
    )


async def handle_confirm_separation(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle confirm_separation action."""
    from tools.separation import confirm_separation_tool

    audit.working(
        f"Confirmando separacao: {payload.get('expedition_id')}",
        session_id=session_id,
    )

    return await confirm_separation_tool(
        expedition_id=payload.get("expedition_id", ""),
        items_confirmed=payload.get("items_confirmed", []),
        package_info=payload.get("package_info", {}),
        operator_id=payload.get("operator_id", "system"),
        session_id=session_id,
    )


async def handle_complete_expedition(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle complete_expedition action."""
    from tools.complete_expedition import complete_expedition_tool

    audit.working(
        f"Completando expedicao: {payload.get('expedition_id')}",
        session_id=session_id,
    )

    return await complete_expedition_tool(
        expedition_id=payload.get("expedition_id", ""),
        nf_number=payload.get("nf_number", ""),
        nf_key=payload.get("nf_key", ""),
        carrier=payload.get("carrier", ""),
        tracking_code=payload.get("tracking_code"),
        operator_id=payload.get("operator_id", "system"),
        session_id=session_id,
    )


async def handle_get_expedition(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle get_expedition action."""
    from tools.process_expedition import get_expedition_tool

    return await get_expedition_tool(
        expedition_id=payload.get("expedition_id", ""),
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
