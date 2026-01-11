# =============================================================================
# EstoqueControlAgent - AgentCore Runtime Entry Point
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# Core agent for inventory movements (+/-). Handles:
# - Reservations for chamados/projetos
# - Expeditions (outgoing shipments)
# - Transfers between locations
# - Returns (reversas)
# - Balance queries
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
#
# Human-in-the-Loop Matrix:
# - Reservation same project: AUTONOMOUS
# - Reservation cross-project: HIL
# - Transfer same project: AUTONOMOUS
# - Transfer to restricted location: HIL
# - Adjustment: ALWAYS HIL
# - Discard/Loss: ALWAYS HIL
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

# Agent definition
from agents.estoque_control.agent import create_estoque_control_agent, AGENT_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

APP_NAME = "sga_inventory"
AGENT_NAME = "EstoqueControlAgent"


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
        _adk_agent = create_estoque_control_agent()
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
    Async agent invocation with inventory control logic.

    Args:
        payload: Parsed payload from A2A message
        context: AgentCore runtime context

    Returns:
        Response dict for A2A protocol
    """
    session_id = getattr(context, "session_id", None) or "default"
    user_id = payload.get("user_id", "system")
    action = payload.get("action", "process")

    # Emit START event for Agent Room
    audit.started(
        message=f"Iniciando: {action}",
        session_id=session_id,
    )

    try:
        with trace_subsegment("estoque_control_invocation", {"action": action}):
            # Route to appropriate handler based on action
            if action == "create_reservation":
                result = await _handle_create_reservation(payload, session_id, user_id)
            elif action == "cancel_reservation":
                result = await _handle_cancel_reservation(payload, session_id, user_id)
            elif action == "process_expedition":
                result = await _handle_process_expedition(payload, session_id, user_id)
            elif action == "create_transfer":
                result = await _handle_create_transfer(payload, session_id, user_id)
            elif action == "process_return":
                result = await _handle_process_return(payload, session_id, user_id)
            elif action == "query_balance":
                result = await _handle_query_balance(payload, session_id)
            elif action == "query_asset_location":
                result = await _handle_query_asset_location(payload, session_id)
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

async def _handle_create_reservation(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Handle reservation creation request."""
    audit.working(
        message="Criando reserva de estoque...",
        session_id=session_id,
    )

    from agents.estoque_control.tools.reservation import create_reservation_tool

    return await create_reservation_tool(
        part_number=payload.get("part_number"),
        quantity=payload.get("quantity", 1),
        project_id=payload.get("project_id"),
        chamado_id=payload.get("chamado_id"),
        serial_numbers=payload.get("serial_numbers"),
        source_location_id=payload.get("source_location_id", "ESTOQUE_CENTRAL"),
        destination_location_id=payload.get("destination_location_id"),
        requested_by=user_id,
        notes=payload.get("notes"),
        ttl_hours=payload.get("ttl_hours", 72),
        session_id=session_id,
    )


async def _handle_cancel_reservation(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Handle reservation cancellation request."""
    audit.working(
        message="Cancelando reserva...",
        session_id=session_id,
    )

    from agents.estoque_control.tools.reservation import cancel_reservation_tool

    return await cancel_reservation_tool(
        reservation_id=payload.get("reservation_id"),
        cancelled_by=user_id,
        reason=payload.get("reason"),
        session_id=session_id,
    )


async def _handle_process_expedition(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Handle expedition processing request."""
    audit.working(
        message="Processando expedição...",
        session_id=session_id,
    )

    from agents.estoque_control.tools.expedition import process_expedition_tool

    return await process_expedition_tool(
        reservation_id=payload.get("reservation_id"),
        part_number=payload.get("part_number"),
        quantity=payload.get("quantity", 1),
        serial_numbers=payload.get("serial_numbers"),
        source_location_id=payload.get("source_location_id", "ESTOQUE_CENTRAL"),
        destination=payload.get("destination", ""),
        project_id=payload.get("project_id"),
        chamado_id=payload.get("chamado_id"),
        recipient_name=payload.get("recipient_name", ""),
        recipient_contact=payload.get("recipient_contact", ""),
        shipping_method=payload.get("shipping_method", "HAND_DELIVERY"),
        processed_by=user_id,
        notes=payload.get("notes"),
        evidence_keys=payload.get("evidence_keys"),
        session_id=session_id,
    )


async def _handle_create_transfer(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Handle transfer creation request."""
    audit.working(
        message="Criando transferência...",
        session_id=session_id,
    )

    from agents.estoque_control.tools.transfer import create_transfer_tool

    return await create_transfer_tool(
        part_number=payload.get("part_number"),
        quantity=payload.get("quantity", 1),
        source_location_id=payload.get("source_location_id"),
        destination_location_id=payload.get("destination_location_id"),
        project_id=payload.get("project_id"),
        serial_numbers=payload.get("serial_numbers"),
        requested_by=user_id,
        notes=payload.get("notes"),
        session_id=session_id,
    )


async def _handle_process_return(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Handle return (reversa) processing request."""
    audit.working(
        message="Processando reversa...",
        session_id=session_id,
    )

    from agents.estoque_control.tools.return_ops import process_return_tool

    return await process_return_tool(
        part_number=payload.get("part_number"),
        quantity=payload.get("quantity", 1),
        serial_numbers=payload.get("serial_numbers"),
        destination_location_id=payload.get("destination_location_id", "ESTOQUE_CENTRAL"),
        project_id=payload.get("project_id", ""),
        chamado_id=payload.get("chamado_id"),
        original_expedition_id=payload.get("original_expedition_id"),
        return_reason=payload.get("return_reason", ""),
        condition=payload.get("condition", "GOOD"),
        processed_by=user_id,
        notes=payload.get("notes"),
        session_id=session_id,
    )


async def _handle_query_balance(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle balance query request."""
    audit.working(
        message="Consultando saldo...",
        session_id=session_id,
    )

    from agents.estoque_control.tools.query import query_balance_tool

    return await query_balance_tool(
        part_number=payload.get("part_number"),
        location_id=payload.get("location_id"),
        project_id=payload.get("project_id"),
        session_id=session_id,
    )


async def _handle_query_asset_location(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle asset location query request."""
    audit.working(
        message="Localizando ativo...",
        session_id=session_id,
    )

    from agents.estoque_control.tools.query import query_asset_location_tool

    return await query_asset_location_tool(
        serial_number=payload.get("serial_number"),
        session_id=session_id,
    )


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

    message = f"Process estoque control action: {json.dumps(payload)}"

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
# Health Check
# =============================================================================

@app.health_check
def health_check() -> Dict[str, Any]:
    """Health check for AgentCore Runtime."""
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "role": "inventory_control",
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
