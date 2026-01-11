# =============================================================================
# LearningAgent - AgentCore Runtime Entry Point
# =============================================================================
# 100% Agentic AI architecture using Google ADK + AWS Bedrock AgentCore.
#
# This agent manages episodic memory for import intelligence:
# - Stores successful import patterns
# - Retrieves prior knowledge for new imports
# - Generates cross-episode reflections
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
# - Memory: AgentCore Memory with GLOBAL namespace (company-wide learning)
# - Tracing: X-Ray distributed tracing for observability
#
# Reference:
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
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

# Shared infrastructure
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import init_xray_tracing, trace_subsegment

# Agent definition
from agents.learning.agent import create_learning_agent, AGENT_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Memory Configuration (GLOBAL namespace - company-wide learning)
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "nexo_agent_mem-Z5uQr8CDGf")
MEMORY_NAMESPACE = "/strategy/import/company"  # GLOBAL (NOT per-user!)

# Agent Configuration
APP_NAME = "sga_inventory"
AGENT_NAME = "LearningAgent"


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
_memory_client = None
_session_service = None


def _get_adk_agent():
    """Lazy-load Google ADK Agent."""
    global _adk_agent
    if _adk_agent is None:
        _adk_agent = create_learning_agent()
        logger.info(f"[{AGENT_NAME}] ADK Agent initialized")
    return _adk_agent


def _get_memory_client():
    """Lazy-load AgentCore Memory client."""
    global _memory_client
    if _memory_client is None:
        try:
            from bedrock_agentcore.memory import MemoryClient
            _memory_client = MemoryClient(memory_id=MEMORY_ID)
            logger.info(f"[{AGENT_NAME}] Memory client initialized: {MEMORY_ID}")
        except ImportError:
            logger.warning(f"[{AGENT_NAME}] Memory SDK not available")
        except Exception as e:
            logger.error(f"[{AGENT_NAME}] Memory init failed: {e}")
    return _memory_client


def _get_session_service():
    """Lazy-load AgentCore Session Service (NOT InMemorySessionService!)."""
    global _session_service
    if _session_service is None:
        try:
            from google.adk.sessions import AgentCoreSessionService
            memory_client = _get_memory_client()
            if memory_client:
                _session_service = AgentCoreSessionService(
                    memory_client=memory_client,
                    namespace=MEMORY_NAMESPACE,
                )
                logger.info(f"[{AGENT_NAME}] AgentCore SessionService initialized")
            else:
                # Fallback to in-memory only if AgentCore unavailable
                from google.adk.sessions import InMemorySessionService
                _session_service = InMemorySessionService()
                logger.warning(f"[{AGENT_NAME}] Using InMemorySessionService (fallback)")
        except ImportError:
            from google.adk.sessions import InMemorySessionService
            _session_service = InMemorySessionService()
            logger.warning(f"[{AGENT_NAME}] AgentCore session not available, using InMemory")
    return _session_service


# =============================================================================
# A2A Protocol Entry Point
# =============================================================================

@app.entrypoint
def agent_invocation(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Entry point for AgentCore Runtime invocations.

    This is called when:
    1. Another agent invokes this agent via A2A protocol
    2. The AgentCore Gateway routes a request to this agent

    Args:
        payload: A2A message payload with action and parameters
        context: AgentCore context (session_id, identity, etc.)

    Returns:
        A2A response with result
    """
    return asyncio.run(_invoke_agent_async(payload, context))


async def _invoke_agent_async(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Async agent invocation with ADK Runner.

    Implements the 100% Agentic pattern:
    1. Parse A2A message
    2. Emit audit events for Agent Room visibility
    3. Run ADK agent with AgentCore session
    4. Return A2A response

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
        message=f"Iniciando ação: {action}",
        session_id=session_id,
    )

    try:
        with trace_subsegment("agent_invocation", {"action": action}):
            # Get ADK agent and session service
            adk_agent = _get_adk_agent()
            session_service = _get_session_service()

            # Build message for ADK runner
            message = _build_message(payload)

            # Emit WORKING event
            audit.working(
                message=f"Processando: {action}",
                session_id=session_id,
                details={"payload_keys": list(payload.keys())},
            )

            # Run ADK agent
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

            # Parse response (expect JSON)
            try:
                result = json.loads(response_text) if response_text else {}
            except json.JSONDecodeError:
                result = {"response": response_text}

            # Emit COMPLETED event
            audit.completed(
                message=f"Concluído: {action}",
                session_id=session_id,
                details={"success": True},
            )

            return {
                "success": True,
                "action": action,
                "result": result,
                "agent_id": AGENT_ID,
            }

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] Error: {e}", exc_info=True)

        # Emit ERROR event
        audit.error(
            message=f"Erro ao processar: {action}",
            session_id=session_id,
            error=str(e),
        )

        return {
            "success": False,
            "action": action,
            "error": str(e),
            "agent_id": AGENT_ID,
        }


def _build_message(payload: Dict[str, Any]) -> str:
    """
    Build message for ADK runner from A2A payload.

    The payload may contain:
    - action: The action to perform (create_episode, retrieve_prior_knowledge, etc.)
    - Parameters specific to the action

    We convert this to a natural language message that the ADK agent
    can process with its tools.

    Args:
        payload: A2A payload

    Returns:
        Natural language message for ADK agent
    """
    action = payload.get("action", "process")

    # Map actions to natural language messages
    if action == "create_episode":
        return f"""Create an import episode with the following data:
- Filename: {payload.get('filename', 'unknown')}
- User ID: {payload.get('user_id', 'unknown')}
- File Analysis: {json.dumps(payload.get('file_analysis', {}))}
- Column Mappings: {json.dumps(payload.get('column_mappings', {}))}
- User Corrections: {json.dumps(payload.get('user_corrections', {}))}
- Import Result: {json.dumps(payload.get('import_result', {}))}
- Target Table: {payload.get('target_table', 'pending_entry_items')}

Store this episode in memory for future learning."""

    elif action == "retrieve_prior_knowledge":
        return f"""Retrieve prior knowledge for import:
- Filename: {payload.get('filename', 'unknown')}
- User ID: {payload.get('user_id', 'unknown')}
- File Analysis: {json.dumps(payload.get('file_analysis', {}))}
- Target Table: {payload.get('target_table', 'pending_entry_items')}

Search for similar past imports and suggest mappings based on learned patterns."""

    elif action == "generate_reflection":
        return f"""Generate reflection for import pattern:
- Filename Pattern: {payload.get('filename_pattern', 'unknown')}
- User ID: {payload.get('user_id', 'unknown')}
- Recent Outcomes: {json.dumps(payload.get('recent_outcomes', []))}

Analyze patterns across episodes and generate insights for improvement."""

    elif action == "get_adaptive_threshold":
        return f"""Calculate adaptive confidence threshold:
- Filename: {payload.get('filename', 'unknown')}
- User ID: {payload.get('user_id', 'unknown')}
- File Analysis: {json.dumps(payload.get('file_analysis', {}))}

Based on historical success rates, determine the appropriate threshold."""

    else:
        # Generic message for unknown actions
        return f"Process the following request: {json.dumps(payload)}"


# =============================================================================
# Health Check
# =============================================================================

@app.health_check
def health_check() -> Dict[str, Any]:
    """
    Health check for AgentCore Runtime.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "memory_id": MEMORY_ID,
        "memory_namespace": MEMORY_NAMESPACE,
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    # Run the AgentCore app
    # Port 9000 is MANDATORY for A2A protocol
    app.run(host="0.0.0.0", port=9000)
