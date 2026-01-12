# =============================================================================
# IntakeAgent - AgentCore Runtime Entry Point
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# Processes incoming materials via NF (Nota Fiscal Eletrônica):
# - Upload and parse NF XML/PDF files
# - AI-assisted data extraction from PDFs/Images
# - Automatic part number matching
# - Serial number detection
# - Entry creation with confidence scoring
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
# - Vision: Gemini Vision for scanned document OCR
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
from shared.a2a_client import delegate_to_learning
from shared.xray_tracer import init_xray_tracing, trace_subsegment, trace_a2a_call
from shared.identity_utils import extract_user_identity, log_identity_context

# Agent definition
from agents.intake.agent import create_intake_agent, AGENT_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

APP_NAME = "sga_inventory"
AGENT_NAME = "IntakeAgent"


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
        _adk_agent = create_intake_agent()
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
    Async agent invocation with NF processing logic.

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
        with trace_subsegment("intake_invocation", {"action": action}):
            # Route to appropriate handler based on action
            if action == "process_nf":
                result = await _handle_process_nf(payload, session_id, user_id)
            elif action == "parse_nf_xml":
                result = await _handle_parse_nf_xml(payload, session_id)
            elif action == "parse_nf_image":
                result = await _handle_parse_nf_image(payload, session_id)
            elif action == "match_items":
                result = await _handle_match_items(payload, session_id)
            elif action == "confirm_entry":
                result = await _handle_confirm_entry(payload, session_id, user_id)
            elif action == "get_upload_url":
                result = await _handle_get_upload_url(payload, session_id)
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

async def _handle_process_nf(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Handle complete NF processing workflow.

    1. Download file from S3
    2. Parse NF (XML or Vision AI for PDF/image)
    3. Match items to part numbers
    4. Calculate confidence
    5. Create pending entry or route to HIL
    """
    audit.working(
        message="Processando NF...",
        session_id=session_id,
    )

    from agents.intake.tools.parse_nf import parse_nf_tool
    from agents.intake.tools.match_items import match_items_tool
    from agents.intake.tools.process_entry import process_entry_tool

    s3_key = payload.get("s3_key")
    file_type = payload.get("file_type", "xml")
    project_id = payload.get("project_id", "")
    destination = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    # Step 1: Parse NF
    audit.working(
        message=f"Lendo NF ({file_type})...",
        session_id=session_id,
    )

    parse_result = await parse_nf_tool(
        s3_key=s3_key,
        file_type=file_type,
        session_id=session_id,
    )

    if not parse_result.get("success"):
        return parse_result

    extraction = parse_result.get("extraction", {})

    # Step 2: Match items to part numbers
    audit.working(
        message=f"Identificando {len(extraction.get('items', []))} itens...",
        session_id=session_id,
    )

    match_result = await match_items_tool(
        items=extraction.get("items", []),
        session_id=session_id,
    )

    # Step 3: Create entry
    audit.working(
        message="Criando entrada...",
        session_id=session_id,
    )

    entry_result = await process_entry_tool(
        extraction=extraction,
        matched_items=match_result.get("matched_items", []),
        unmatched_items=match_result.get("unmatched_items", []),
        project_id=project_id,
        destination_location_id=destination,
        uploaded_by=user_id,
        s3_key=s3_key,
        file_type=file_type,
        session_id=session_id,
    )

    # Step 4: Store learning episode if successful
    if entry_result.get("success"):
        await _store_learning_episode(
            extraction=extraction,
            match_result=match_result,
            user_id=user_id,
            session_id=session_id,
        )

    return entry_result


async def _handle_parse_nf_xml(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Parse NF XML file."""
    audit.working(
        message="Parseando XML da NF...",
        session_id=session_id,
    )

    from agents.intake.tools.parse_nf import parse_nf_tool

    return await parse_nf_tool(
        s3_key=payload.get("s3_key"),
        file_type="xml",
        session_id=session_id,
    )


async def _handle_parse_nf_image(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Parse NF from image/PDF using Vision AI."""
    audit.working(
        message="Extraindo dados com Vision AI...",
        session_id=session_id,
    )

    from agents.intake.tools.parse_nf import parse_nf_tool

    return await parse_nf_tool(
        s3_key=payload.get("s3_key"),
        file_type="image",
        session_id=session_id,
    )


async def _handle_match_items(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Match NF items to part numbers."""
    audit.working(
        message="Identificando part numbers...",
        session_id=session_id,
    )

    from agents.intake.tools.match_items import match_items_tool

    return await match_items_tool(
        items=payload.get("items", []),
        session_id=session_id,
    )


async def _handle_confirm_entry(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Confirm pending entry and create movements."""
    audit.working(
        message="Confirmando entrada...",
        session_id=session_id,
    )

    from agents.intake.tools.confirm_entry import confirm_entry_tool

    return await confirm_entry_tool(
        entry_id=payload.get("entry_id"),
        confirmed_by=user_id,
        item_mappings=payload.get("item_mappings"),
        notes=payload.get("notes"),
        session_id=session_id,
    )


async def _handle_get_upload_url(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Generate presigned URL for NF upload."""
    try:
        from tools.s3_client import SGAS3Client

        s3 = SGAS3Client()
        filename = payload.get("filename", "upload.xml")
        content_type = payload.get("content_type", "application/xml")

        key = s3.get_temp_path(filename)
        url_info = s3.generate_upload_url(
            key=key,
            content_type=content_type,
            expires_in=3600,
        )

        return {
            "success": True,
            **url_info,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =============================================================================
# A2A Delegation
# =============================================================================

@trace_a2a_call("learning")
async def _store_learning_episode(
    extraction: Dict[str, Any],
    match_result: Dict[str, Any],
    user_id: str,
    session_id: str,
) -> None:
    """Store learning episode for future NF processing."""
    audit.delegating(
        target_agent="learning",
        message="Registrando aprendizado...",
        session_id=session_id,
    )

    try:
        await delegate_to_learning({
            "action": "create_episode",
            "user_id": user_id,
            "episode_type": "nf_processing",
            "data": {
                "emitente_cnpj": extraction.get("emitente", {}).get("cnpj"),
                "emitente_nome": extraction.get("emitente", {}).get("nome"),
                "matched_count": len(match_result.get("matched_items", [])),
                "unmatched_count": len(match_result.get("unmatched_items", [])),
                "item_patterns": _extract_item_patterns(match_result.get("matched_items", [])),
            },
        }, session_id=session_id)
    except Exception as e:
        logger.warning(f"[{AGENT_NAME}] Failed to store learning episode: {e}")


def _extract_item_patterns(matched_items: list) -> list:
    """Extract successful matching patterns for learning."""
    patterns = []
    for item in matched_items[:10]:  # Limit for memory
        patterns.append({
            "supplier_code": item.get("codigo"),
            "description_keywords": item.get("descricao", "")[:50],
            "matched_pn": item.get("matched_pn"),
            "match_method": item.get("match_method"),
        })
    return patterns


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
    action = payload.get("action", "process")
    return f"Process NF action '{action}': {json.dumps(payload)}"


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
