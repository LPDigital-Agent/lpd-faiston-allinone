# =============================================================================
# ReconciliacaoAgent - Main Entry Point
# AWS Bedrock AgentCore Runtime
# =============================================================================
# Agent for inventory reconciliation and counting campaigns.
#
# Features:
# - Start and manage inventory counting campaigns
# - Process count submissions from mobile devices
# - Detect divergences between system and physical counts
# - Propose adjustments (ALWAYS requires HIL)
# - Analyze patterns in divergences
# =============================================================================

import asyncio
import logging
import os
from typing import Dict, Any

from google.adk.runners import Runner
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import create_reconciliacao_agent, AGENT_ID
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

    Handles reconciliation operations:
    - start_campaign: Create counting campaign
    - submit_count: Process count submission
    - analyze_divergences: Analyze patterns
    - propose_adjustment: Create adjustment HIL task
    - complete_campaign: Finalize campaign
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """Async agent invocation handler."""
    session_id = getattr(context, "session_id", None)

    audit.started(
        "Iniciando operacao de reconciliacao...",
        session_id=session_id,
    )

    try:
        action = payload.get("action", "")

        # Extract user identity from AgentCore context (JWT validated) or payload (fallback)
        # COMPLIANCE: AgentCore Identity v1.0
        user = extract_user_identity(context, payload)
        user_id = user.user_id

        # Log identity context for security monitoring
        log_identity_context(user, "ReconciliacaoAgent", action, session_id)

        # Route to appropriate handler
        if action == "start_campaign":
            result = await handle_start_campaign(payload, session_id)
        elif action == "submit_count":
            result = await handle_submit_count(payload, session_id)
        elif action == "analyze_divergences":
            result = await handle_analyze_divergences(payload, session_id)
        elif action == "propose_adjustment":
            result = await handle_propose_adjustment(payload, session_id)
        elif action == "complete_campaign":
            result = await handle_complete_campaign(payload, session_id)
        elif action == "get_campaign":
            result = await handle_get_campaign(payload, session_id)
        elif action == "get_campaign_items":
            result = await handle_get_campaign_items(payload, session_id)
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
        logger.error(f"[ReconciliacaoAgent] Error: {e}", exc_info=True)
        audit.error(
            "Erro na reconciliacao",
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

    agent = create_reconciliacao_agent()
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


async def handle_start_campaign(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle start_campaign action."""
    from tools.campaign import start_campaign_tool

    audit.working(
        f"Criando campanha: {payload.get('name', 'N/A')}",
        session_id=session_id,
    )

    return await start_campaign_tool(
        name=payload.get("name", ""),
        description=payload.get("description", ""),
        location_ids=payload.get("location_ids"),
        project_ids=payload.get("project_ids"),
        part_numbers=payload.get("part_numbers"),
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        created_by=payload.get("created_by", "system"),
        require_double_count=payload.get("require_double_count", False),
        session_id=session_id,
    )


async def handle_submit_count(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle submit_count action."""
    from tools.counting import submit_count_tool

    audit.working(
        f"Processando contagem: {payload.get('part_number')} @ {payload.get('location_id')}",
        session_id=session_id,
    )

    return await submit_count_tool(
        campaign_id=payload.get("campaign_id", ""),
        part_number=payload.get("part_number", ""),
        location_id=payload.get("location_id", ""),
        counted_quantity=payload.get("counted_quantity", 0),
        counted_serials=payload.get("counted_serials"),
        counted_by=payload.get("counted_by", "system"),
        evidence_keys=payload.get("evidence_keys"),
        notes=payload.get("notes"),
        session_id=session_id,
    )


async def handle_analyze_divergences(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle analyze_divergences action."""
    from tools.divergence import analyze_divergences_tool

    audit.working(
        f"Analisando divergencias da campanha: {payload.get('campaign_id')}",
        session_id=session_id,
    )

    return await analyze_divergences_tool(
        campaign_id=payload.get("campaign_id", ""),
        session_id=session_id,
    )


async def handle_propose_adjustment(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle propose_adjustment action."""
    from tools.adjustment import propose_adjustment_tool

    audit.working(
        f"Propondo ajuste: {payload.get('part_number')} @ {payload.get('location_id')}",
        session_id=session_id,
    )

    return await propose_adjustment_tool(
        campaign_id=payload.get("campaign_id", ""),
        part_number=payload.get("part_number", ""),
        location_id=payload.get("location_id", ""),
        proposed_by=payload.get("proposed_by", "system"),
        adjustment_reason=payload.get("adjustment_reason", ""),
        session_id=session_id,
    )


async def handle_complete_campaign(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle complete_campaign action."""
    from tools.campaign import complete_campaign_tool

    audit.working(
        f"Finalizando campanha: {payload.get('campaign_id')}",
        session_id=session_id,
    )

    return await complete_campaign_tool(
        campaign_id=payload.get("campaign_id", ""),
        completed_by=payload.get("completed_by", "system"),
        session_id=session_id,
    )


async def handle_get_campaign(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle get_campaign action."""
    from tools.campaign import get_campaign_tool

    return await get_campaign_tool(
        campaign_id=payload.get("campaign_id", ""),
        session_id=session_id,
    )


async def handle_get_campaign_items(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle get_campaign_items action."""
    from tools.campaign import get_campaign_items_tool

    return await get_campaign_items_tool(
        campaign_id=payload.get("campaign_id", ""),
        status=payload.get("status"),
        session_id=session_id,
    )


# =============================================================================
# Health Check
# =============================================================================


@app.ping
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
