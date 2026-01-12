# =============================================================================
# ComplianceAgent - AgentCore Runtime Entry Point
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# Features:
# - Validate operations against business rules
# - Check approval requirements
# - Manage approval hierarchies
# - Audit compliance status
# - Flag policy violations
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
# =============================================================================

import asyncio
import json
import logging
from typing import Dict, Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import init_xray_tracing, trace_subsegment
from shared.identity_utils import extract_user_identity, log_identity_context

from agents.compliance.agent import create_compliance_agent, AGENT_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_NAME = "sga_inventory"
AGENT_NAME = "ComplianceAgent"

app = BedrockAgentCoreApp()
init_xray_tracing(service_name=f"sga-{AGENT_ID}")
audit = AgentAuditEmitter(agent_id=AGENT_ID)

_adk_agent = None
_session_service = None


def _get_adk_agent():
    global _adk_agent
    if _adk_agent is None:
        _adk_agent = create_compliance_agent()
        logger.info(f"[{AGENT_NAME}] ADK Agent initialized")
    return _adk_agent


def _get_session_service():
    global _session_service
    if _session_service is None:
        _session_service = InMemorySessionService()
    return _session_service


@app.entrypoint
def agent_invocation(payload: Dict[str, Any], context) -> Dict[str, Any]:
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    session_id = getattr(context, "session_id", None) or "default"
    action = payload.get("action", "process")

    # Extract user identity from AgentCore context (JWT validated) or payload (fallback)
    # COMPLIANCE: AgentCore Identity v1.0
    user = extract_user_identity(context, payload)
    user_id = user.user_id

    # Log identity context for security monitoring
    log_identity_context(user, AGENT_NAME, action, session_id)

    audit.started(message=f"Iniciando: {action}", session_id=session_id)

    try:
        with trace_subsegment("compliance_invocation", {"action": action}):
            if action == "validate_operation":
                result = await _handle_validate_operation(payload, session_id)
            elif action == "check_approval":
                result = await _handle_check_approval(payload, session_id)
            elif action == "audit_compliance":
                result = await _handle_audit_compliance(payload, session_id)
            elif action == "flag_violation":
                result = await _handle_flag_violation(payload, session_id, user_id)
            elif action == "get_approval_requirements":
                result = await _handle_get_approval_requirements(payload, session_id)
            else:
                result = await _invoke_adk_agent(payload, session_id, user_id)

            audit.completed(
                message=f"Concluído: {action}",
                session_id=session_id,
                details={"success": result.get("success", True)},
            )

            return {"success": result.get("success", True), "action": action, "result": result, "agent_id": AGENT_ID}

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] Error: {e}", exc_info=True)
        audit.error(message=f"Erro: {action}", session_id=session_id, error=str(e))
        return {"success": False, "action": action, "error": str(e), "agent_id": AGENT_ID}


async def _handle_validate_operation(payload: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    audit.working(message="Validando operação contra políticas...", session_id=session_id)
    from agents.compliance.tools.validate_operation import validate_operation_tool
    return await validate_operation_tool(
        operation_type=payload.get("operation_type"),
        part_number=payload.get("part_number"),
        quantity=payload.get("quantity", 1),
        source_location=payload.get("source_location"),
        destination_location=payload.get("destination_location"),
        source_project=payload.get("source_project"),
        destination_project=payload.get("destination_project"),
        total_value=payload.get("total_value"),
        user_id=payload.get("user_id", "system"),
        session_id=session_id,
    )


async def _handle_check_approval(payload: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    audit.working(message="Verificando status de aprovação...", session_id=session_id)
    from agents.compliance.tools.check_approval import check_approval_status_tool
    return await check_approval_status_tool(
        entity_type=payload.get("entity_type"),
        entity_id=payload.get("entity_id"),
        required_role=payload.get("required_role"),
        session_id=session_id,
    )


async def _handle_audit_compliance(payload: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    audit.working(message="Executando auditoria de compliance...", session_id=session_id)
    from agents.compliance.tools.audit_compliance import audit_compliance_tool
    return await audit_compliance_tool(
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        location_id=payload.get("location_id"),
        project_id=payload.get("project_id"),
        session_id=session_id,
    )


async def _handle_flag_violation(payload: Dict[str, Any], session_id: str, user_id: str) -> Dict[str, Any]:
    audit.working(message="Registrando violação...", session_id=session_id)
    from agents.compliance.tools.flag_violation import flag_violation_tool
    return await flag_violation_tool(
        entity_type=payload.get("entity_type"),
        entity_id=payload.get("entity_id"),
        violation_type=payload.get("violation_type"),
        description=payload.get("description"),
        severity=payload.get("severity", "MEDIUM"),
        flagged_by=user_id,
        session_id=session_id,
    )


async def _handle_get_approval_requirements(payload: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    audit.working(message="Consultando requisitos de aprovação...", session_id=session_id)
    from agents.compliance.tools.approval_requirements import get_approval_requirements_tool
    return await get_approval_requirements_tool(
        operation_type=payload.get("operation_type"),
        session_id=session_id,
    )


async def _invoke_adk_agent(payload: Dict[str, Any], session_id: str, user_id: str) -> Dict[str, Any]:
    adk_agent = _get_adk_agent()
    session_service = _get_session_service()
    runner = Runner(agent=adk_agent, app_name=APP_NAME, session_service=session_service)
    response_text = ""
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=json.dumps(payload)):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    response_text += part.text
    try:
        return json.loads(response_text) if response_text else {}
    except json.JSONDecodeError:
        return {"response": response_text}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
