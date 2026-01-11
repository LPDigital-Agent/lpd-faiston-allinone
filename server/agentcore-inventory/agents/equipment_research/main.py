# =============================================================================
# EquipmentResearchAgent - Main Entry Point
# AWS Bedrock AgentCore Runtime
# =============================================================================
# AI-First agent that researches equipment documentation after imports.
# Uses Gemini with google_search grounding to find official manuals,
# datasheets, and specifications from manufacturer websites.
#
# Features:
# - Generate optimized search queries
# - Execute web searches with grounding
# - Download and upload documents to S3
# - Create Bedrock KB metadata
# =============================================================================

import asyncio
import logging
import os
from typing import Dict, Any, List

from google.adk.runners import Runner
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import create_equipment_research_agent, AGENT_ID
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

    Handles research operations:
    - research_equipment: Research docs for single equipment
    - research_batch: Research docs for multiple equipment
    - generate_queries: Generate search queries only
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """Async agent invocation handler."""
    session_id = getattr(context, "session_id", None)

    audit.started(
        "Iniciando pesquisa de documentação...",
        session_id=session_id,
    )

    try:
        action = payload.get("action", "")
        user_id = payload.get("user_id", "system")

        # Route to appropriate handler
        if action == "research_equipment":
            result = await handle_research_equipment(payload, session_id)
        elif action == "research_batch":
            result = await handle_research_batch(payload, session_id)
        elif action == "generate_queries":
            result = await handle_generate_queries(payload, session_id)
        else:
            # Use ADK Runner for conversational queries
            result = await run_adk_agent(payload, session_id, user_id)

        audit.completed(
            f"Pesquisa concluída: {action or 'consulta'}",
            session_id=session_id,
            details={"action": action},
        )

        return result

    except Exception as e:
        logger.error(f"[EquipmentResearchAgent] Error: {e}", exc_info=True)
        audit.error(
            "Erro na pesquisa de documentação",
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

    agent = create_equipment_research_agent()
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


async def handle_research_equipment(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle research_equipment action."""
    from tools.research_equipment import research_equipment_tool

    part_number = payload.get("part_number", "")
    description = payload.get("description", "")

    audit.working(
        f"Pesquisando documentação: {part_number}",
        session_id=session_id,
        details={
            "part_number": part_number,
            "description": description[:50] if description else "",
        },
    )

    return await research_equipment_tool(
        part_number=part_number,
        description=description,
        manufacturer=payload.get("manufacturer"),
        serial_number=payload.get("serial_number"),
        additional_info=payload.get("additional_info"),
        session_id=session_id,
    )


async def handle_research_batch(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle research_batch action."""
    from tools.research_equipment import research_equipment_tool

    equipment_list = payload.get("equipment_list", [])

    audit.working(
        f"Pesquisando {len(equipment_list)} equipamentos em lote",
        session_id=session_id,
    )

    results = []
    for idx, equipment in enumerate(equipment_list):
        audit.working(
            f"Pesquisando equipamento {idx + 1}/{len(equipment_list)}: {equipment.get('part_number', '')}",
            session_id=session_id,
        )

        result = await research_equipment_tool(
            part_number=equipment.get("part_number", ""),
            description=equipment.get("description", ""),
            manufacturer=equipment.get("manufacturer"),
            serial_number=equipment.get("serial_number"),
            additional_info=equipment.get("additional_info"),
            session_id=session_id,
        )
        results.append(result)

        # Check if rate limited
        if result.get("status") == "RATE_LIMITED":
            # Mark remaining as rate limited
            for remaining in equipment_list[idx + 1:]:
                results.append({
                    "success": False,
                    "part_number": remaining.get("part_number", ""),
                    "status": "RATE_LIMITED",
                    "error": "Daily quota exceeded",
                })
            break

    return {
        "success": True,
        "results": results,
        "total": len(equipment_list),
        "completed": sum(1 for r in results if r.get("status") == "COMPLETED"),
        "failed": sum(1 for r in results if r.get("status") in ["FAILED", "RATE_LIMITED"]),
    }


async def handle_generate_queries(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Handle generate_queries action."""
    from tools.generate_queries import generate_queries_tool

    audit.working(
        f"Gerando queries para: {payload.get('part_number', '')}",
        session_id=session_id,
    )

    return await generate_queries_tool(
        part_number=payload.get("part_number", ""),
        description=payload.get("description", ""),
        manufacturer=payload.get("manufacturer"),
        additional_info=payload.get("additional_info"),
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
