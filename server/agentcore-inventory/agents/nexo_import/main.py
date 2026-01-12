# =============================================================================
# NexoImportAgent - AgentCore Runtime Entry Point (Orchestrator)
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# This is the MAIN ORCHESTRATOR for the import flow:
# - OBSERVE: Analyze file structure
# - THINK: Reason about mappings (with schema context)
# - ASK: Generate questions for HIL (Human-in-the-Loop)
# - LEARN: Delegate to LearningAgent via A2A
# - ACT: Execute import with validated mappings
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
# - Delegation: Calls LearningAgent, SchemaEvolutionAgent via A2A
# - Memory: Delegates to LearningAgent (no direct memory access)
#
# Reference:
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
# =============================================================================

import asyncio
import os
import json
import logging
from typing import Dict, Any, Optional

# AgentCore Runtime
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Google ADK
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Shared infrastructure
from shared.audit_emitter import AgentAuditEmitter
from shared.a2a_client import (
    A2AClient,
    delegate_to_learning,
    delegate_to_schema_evolution,
)
from shared.xray_tracer import init_xray_tracing, trace_subsegment, trace_a2a_call
from shared.identity_utils import extract_user_identity, log_identity_context

# Agent definition
from agents.nexo_import.agent import create_nexo_import_agent, AGENT_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

APP_NAME = "sga_inventory"
AGENT_NAME = "NexoImportAgent"


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
_a2a_client = None


def _get_adk_agent():
    """Lazy-load Google ADK Agent."""
    global _adk_agent
    if _adk_agent is None:
        _adk_agent = create_nexo_import_agent()
        logger.info(f"[{AGENT_NAME}] ADK Agent initialized")
    return _adk_agent


def _get_session_service():
    """Lazy-load Session Service (stateless - InMemory)."""
    global _session_service
    if _session_service is None:
        _session_service = InMemorySessionService()
        logger.info(f"[{AGENT_NAME}] InMemory SessionService initialized")
    return _session_service


def _get_a2a_client():
    """Lazy-load A2A Client for inter-agent communication."""
    global _a2a_client
    if _a2a_client is None:
        _a2a_client = A2AClient()
        logger.info(f"[{AGENT_NAME}] A2A Client initialized")
    return _a2a_client


# =============================================================================
# A2A Protocol Entry Point
# =============================================================================

@app.entrypoint
def agent_invocation(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Entry point for AgentCore Runtime invocations.

    This is called when:
    1. Frontend calls this agent via AgentCore Gateway
    2. Another agent invokes this agent via A2A protocol

    Args:
        payload: A2A message payload with action and parameters
        context: AgentCore context (session_id, identity, etc.)

    Returns:
        A2A response with result
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Async agent invocation with orchestration logic.

    The NexoImportAgent is the ORCHESTRATOR - it coordinates the flow
    and delegates to specialized agents via A2A protocol.

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
        with trace_subsegment("orchestrator_invocation", {"action": action}):
            # Route to appropriate handler based on action
            if action == "analyze_file":
                result = await _handle_analyze_file(payload, session_id, user_id)
            elif action == "reason_mappings":
                result = await _handle_reason_mappings(payload, session_id, user_id)
            elif action == "process_answers":
                result = await _handle_process_answers(payload, session_id, user_id)
            elif action == "execute_import":
                result = await _handle_execute_import(payload, session_id, user_id)
            elif action == "get_prior_knowledge":
                # Delegate to LearningAgent via A2A
                result = await _delegate_to_learning(payload, session_id)
            elif action == "create_episode":
                # Delegate to LearningAgent via A2A
                result = await _delegate_create_episode(payload, session_id)
            elif action == "create_column":
                # Delegate to SchemaEvolutionAgent via A2A
                result = await _delegate_to_schema_evolution(payload, session_id)
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

async def _handle_analyze_file(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Handle file analysis (OBSERVE phase).

    1. Analyze file structure using sheet_analyzer
    2. Get prior knowledge from LearningAgent via A2A
    3. Return analysis with suggested mappings
    """
    audit.working(
        message="Analisando estrutura do arquivo...",
        session_id=session_id,
    )

    s3_key = payload.get("s3_key")
    filename = payload.get("filename")

    # Step 1: Analyze file structure
    file_analysis = await _analyze_file_structure(s3_key)

    # Step 2: Get prior knowledge via A2A (DELEGATION)
    audit.delegating(
        target_agent="learning",
        message="Consultando conhecimento prévio...",
        session_id=session_id,
    )

    prior_knowledge = await delegate_to_learning({
        "action": "retrieve_prior_knowledge",
        "user_id": user_id,
        "filename": filename,
        "file_analysis": file_analysis,
    }, session_id=session_id)

    # Combine analysis with prior knowledge
    return {
        "success": True,
        "file_analysis": file_analysis,
        "prior_knowledge": prior_knowledge.response if prior_knowledge.success else {},
        "has_prior_knowledge": prior_knowledge.success and "has_prior_knowledge" in str(prior_knowledge.response),
    }


async def _handle_reason_mappings(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Handle mapping reasoning (THINK phase).

    Use ADK agent to reason about column mappings
    with schema context and prior knowledge.
    """
    audit.working(
        message="Raciocinando sobre mapeamentos...",
        session_id=session_id,
    )

    return await _invoke_adk_agent(payload, session_id, user_id)


async def _handle_process_answers(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Handle user answers (ASK → LEARN phase).

    Process user responses and update mappings.
    """
    audit.working(
        message="Processando suas respostas...",
        session_id=session_id,
    )

    return await _invoke_adk_agent(payload, session_id, user_id)


async def _handle_execute_import(
    payload: Dict[str, Any],
    session_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Handle import execution (ACT phase).

    1. Validate mappings against schema
    2. Execute import
    3. Create episode in LearningAgent via A2A
    """
    audit.working(
        message="Executando importação...",
        session_id=session_id,
    )

    # Execute import via ADK agent
    result = await _invoke_adk_agent(payload, session_id, user_id)

    # If successful, create episode for learning
    if result.get("success"):
        audit.delegating(
            target_agent="learning",
            message="Registrando aprendizado...",
            session_id=session_id,
        )

        await delegate_to_learning({
            "action": "create_episode",
            "user_id": user_id,
            "filename": payload.get("filename"),
            "file_analysis": payload.get("file_analysis", {}),
            "column_mappings": payload.get("column_mappings", {}),
            "user_corrections": payload.get("user_corrections", {}),
            "import_result": result,
        }, session_id=session_id)

    return result


# =============================================================================
# A2A Delegation (Inter-Agent Communication)
# =============================================================================

@trace_a2a_call("learning")
async def _delegate_to_learning(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Delegate to LearningAgent via A2A protocol."""
    audit.delegating(
        target_agent="learning",
        message="Consultando agente de memória...",
        session_id=session_id,
    )

    response = await delegate_to_learning(payload, session_id=session_id)
    return json.loads(response.response) if response.success else {"error": response.error}


@trace_a2a_call("learning")
async def _delegate_create_episode(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Delegate episode creation to LearningAgent via A2A protocol."""
    audit.delegating(
        target_agent="learning",
        message="Registrando episódio de aprendizado...",
        session_id=session_id,
    )

    response = await delegate_to_learning({
        **payload,
        "action": "create_episode",
    }, session_id=session_id)

    return json.loads(response.response) if response.success else {"error": response.error}


@trace_a2a_call("schema_evolution")
async def _delegate_to_schema_evolution(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Delegate column creation to SchemaEvolutionAgent via A2A protocol."""
    audit.delegating(
        target_agent="schema_evolution",
        message=f"Criando coluna: {payload.get('column_name')}...",
        session_id=session_id,
    )

    response = await delegate_to_schema_evolution(payload, session_id=session_id)
    return json.loads(response.response) if response.success else {"error": response.error}


# =============================================================================
# Helper Functions
# =============================================================================

async def _analyze_file_structure(s3_key: str) -> Dict[str, Any]:
    """Analyze file structure using sheet_analyzer tool."""
    try:
        from tools.sheet_analyzer import SheetAnalyzer
        analyzer = SheetAnalyzer()
        return await analyzer.analyze_from_s3(s3_key)
    except Exception as e:
        logger.error(f"[{AGENT_NAME}] File analysis failed: {e}")
        return {"error": str(e), "sheets": []}


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

    if action == "reason_mappings":
        return f"""Reason about column mappings for this import:

File Analysis: {json.dumps(payload.get('file_analysis', {}))}
Prior Knowledge: {json.dumps(payload.get('prior_knowledge', {}))}
Schema Context: {payload.get('schema_context', '')}

Generate suggested mappings with confidence scores.
For columns with low confidence (<0.8), generate clarification questions."""

    elif action == "process_answers":
        return f"""Process user answers and update mappings:

Current Mappings: {json.dumps(payload.get('current_mappings', {}))}
User Answers: {json.dumps(payload.get('answers', {}))}
AI Instructions: {json.dumps(payload.get('ai_instructions', {}))}

Update mappings based on user input."""

    elif action == "execute_import":
        return f"""Execute the import with validated mappings:

S3 Key: {payload.get('s3_key')}
Column Mappings: {json.dumps(payload.get('column_mappings', {}))}
Target Table: {payload.get('target_table', 'pending_entry_items')}

Validate and execute the import."""

    return f"Process: {json.dumps(payload)}"


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
