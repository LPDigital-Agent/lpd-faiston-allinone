# =============================================================================
# Faiston Inventory Management - Strands Orchestrator Agent
# =============================================================================
# REFACTORED: 2026-01-14 - Architecture Transformation (Phase 7.1 + Phase 8)
#
# PATTERN: BedrockAgentCoreApp + Strands Agent + Strands Swarm
# DEPLOYMENT: HTTP /invocations (port 8080)
# ROUTING: Gemini Flash decides which specialist agent to invoke
# DISCOVERY: A2AToolProvider for dynamic AgentCard discovery
#
# This orchestrator supports TWO modes:
# 1. Agents-as-Tools (A2A) - Default for most operations
# 2. Strands Swarm - Autonomous multi-agent for NEXO imports
#
# Phase 7.1 Enhancement: Dynamic agent discovery via A2A Protocol
# - AgentCards fetched at startup from /.well-known/agent-card.json
# - System prompt generated from discovered skills
# - Backward compatibility maintained for direct action requests
#
# Phase 8 Enhancement: 100% Autonomous Swarm for Imports
# - 5-agent Swarm: file_analyst, schema_validator, memory_agent, hil_agent, import_executor
# - Autonomous handoffs with stop_action for HIL pause
# - Meta-Tooling enabled for self-improvement
# - See docs/plans/SWARM_ARCHITECTURE_DESIGN.md for full architecture
#
# Architecture validated against Strands documentation:
# - https://strandsagents.com/latest/documentation/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/
#
# Module: Gestao de Ativos -> Gestao de Estoque
# =============================================================================

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool, ToolContext
import asyncio
import json
import logging
import os
from typing import Optional

# Lazy imports for fast cold start
from agents.utils import create_gemini_model, AGENT_VERSION

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "inventory_management"
AGENT_NAME = "FaistonInventoryManagement"

# Feature flag for dynamic discovery (Phase 7.1)
# Set to True to use A2AToolProvider, False for static routing
USE_DYNAMIC_DISCOVERY = os.environ.get("USE_DYNAMIC_DISCOVERY", "false").lower() == "true"

# Feature flag for Swarm-based import (Phase 8)
# Set to True to use Strands Swarm for NEXO import operations
# When True: nexo_* actions route to autonomous 5-agent Swarm
# When False: nexo_* actions route to legacy nexo_import A2A agent
USE_SWARM_IMPORT = os.environ.get("USE_SWARM_IMPORT", "true").lower() == "true"

# =============================================================================
# Default System Prompt (Fallback when discovery fails)
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """
## 🎯 You are Faiston Inventory Management Orchestrator

You are the central intelligence for the SGA (Sistema de Gestão de Ativos - Asset Management System).
Your role is to:
1. UNDERSTAND the user's intent from their message
2. IDENTIFY which specialist agent should handle the request
3. INVOKE the appropriate specialist via the invoke_specialist tool
4. RETURN the specialist's response to the user

## 📋 Available Specialist Agents

| Agent ID | Capabilities | When to Use |
|----------|-------------|-------------|
| estoque_control | Reservations, expeditions, transfers, returns, balance queries | Stock movements, inventory operations |
| intake | NF (Nota Fiscal) PDF/XML extraction and processing | Document intake, invoice processing |
| nexo_import | Smart file import with AI analysis (CSV, XLSX, PDF) | File analysis, data import, schema mapping |
| learning | Prior knowledge retrieval, pattern learning | Historical patterns, memory queries |
| validation | Data and schema validation | Data quality checks |
| reconciliacao | Inventory counts, divergence analysis | Physical counting, reconciliation |
| compliance | Policy validation, approval workflows | HIL tasks, approvals, policy checks |
| carrier | Shipping quotes, carrier recommendation, tracking | Logistics, shipping |
| expedition | Expedition processing, stock verification, SAP export | Outbound logistics |
| reverse | Return processing, condition evaluation | Reverse logistics, returns |
| observation | Audit logging, import analysis | Observations, audit trail |
| schema_evolution | Column type inference, schema changes | Schema analysis |
| equipment_research | Equipment documentation research | Equipment specs, datasheets |
| data_import | Generic data import operations | Bulk imports |

## 🔄 Routing Rules

Use the invoke_specialist tool with the appropriate agent_id:

1. **File Analysis/Import** → agent_id="nexo_import"
2. **NF (Nota Fiscal) Processing** → agent_id="intake"
3. **Stock Movements** → agent_id="estoque_control"
4. **Inventory Counting** → agent_id="reconciliacao"
5. **Approval Workflows** → agent_id="compliance"
6. **Shipping/Logistics** → agent_id="carrier"
7. **Expedition** → agent_id="expedition"
8. **Returns** → agent_id="reverse"
9. **Equipment Research** → agent_id="equipment_research"
10. **Learning/Memory** → agent_id="learning"

## ⚠️ Response Format

Always return the specialist's response as-is in JSON format.
The response should include:
- success: boolean indicating operation result
- specialist_agent: which agent handled the request
- response: the actual data/result from the specialist
"""

# =============================================================================
# Lazy-loaded Components
# =============================================================================

_a2a_client = None
_tool_provider = None
_orchestrator = None
_action_mapping = None
_inventory_swarm = None
_swarm_sessions = {}  # session_id -> SwarmSession state


def _get_a2a_client():
    """Lazy-load A2A client for agent invocations."""
    global _a2a_client
    if _a2a_client is None:
        from shared.a2a_client import A2AClient

        _a2a_client = A2AClient()
    return _a2a_client


async def _get_tool_provider():
    """
    Lazy-load A2A Tool Provider with agent discovery.

    Phase 7.1: Uses A2AToolProvider to discover agents dynamically.
    """
    global _tool_provider
    if _tool_provider is None:
        from shared.a2a_tool_provider import A2AToolProvider

        _tool_provider = A2AToolProvider()
        await _tool_provider.discover_all_agents()
        logger.info(
            f"[Orchestrator] Discovered {len(_tool_provider.discovered_agents)} agents "
            f"with {len(_tool_provider.skill_to_agent)} skills"
        )
    return _tool_provider


def _get_action_mapping():
    """
    Get action-to-specialist mapping.

    When USE_DYNAMIC_DISCOVERY is True, builds mapping from discovered skills.
    Otherwise, uses static fallback mapping.
    """
    global _action_mapping
    if _action_mapping is not None:
        return _action_mapping

    if USE_DYNAMIC_DISCOVERY and _tool_provider:
        _action_mapping = _tool_provider.build_action_mapping()
    else:
        # Static fallback mapping (backward compatibility)
        _action_mapping = _get_static_action_mapping()

    return _action_mapping


def _get_static_action_mapping():
    """
    Static action-to-specialist mapping for backward compatibility.

    This is the fallback when dynamic discovery is disabled or fails.
    """
    return {
        # EstoqueControl
        "where_is_serial": ("estoque_control", "query_asset_location"),
        "get_balance": ("estoque_control", "query_balance"),
        "create_movement": ("estoque_control", "create_movement"),
        "create_reservation": ("estoque_control", "create_reservation"),
        "cancel_reservation": ("estoque_control", "cancel_reservation"),
        "process_expedition": ("estoque_control", "process_expedition"),
        "create_transfer": ("estoque_control", "create_transfer"),
        # Intake
        "process_nf_upload": ("intake", "process_nf"),
        "validate_nf_extraction": ("intake", "validate_extraction"),
        "confirm_nf_entry": ("intake", "confirm_entry"),
        "process_scanned_nf_upload": ("intake", "process_nf"),
        "process_image_ocr": ("intake", "parse_nf_image"),
        # NexoImport
        "nexo_analyze_file": ("nexo_import", "analyze_file"),
        "nexo_get_questions": ("nexo_import", "get_questions"),
        "nexo_submit_answers": ("nexo_import", "submit_answers"),
        "nexo_learn_from_import": ("nexo_import", "learn_from_import"),
        "nexo_prepare_processing": ("nexo_import", "prepare_for_processing"),
        "nexo_execute_import": ("nexo_import", "execute_import"),
        "nexo_get_prior_knowledge": ("nexo_import", "get_prior_knowledge"),
        "nexo_get_adaptive_threshold": ("nexo_import", "get_adaptive_threshold"),
        # Reconciliacao
        "start_inventory_count": ("reconciliacao", "start_campaign"),
        "submit_count_result": ("reconciliacao", "submit_count"),
        "analyze_divergences": ("reconciliacao", "analyze_divergences"),
        "propose_adjustment": ("reconciliacao", "propose_adjustment"),
        # DataImport
        "preview_import": ("data_import", "preview_import"),
        "execute_import": ("data_import", "execute_import"),
        "preview_sap_import": ("data_import", "preview_import"),
        "execute_sap_import": ("data_import", "execute_sap_import"),
        "validate_pn_mapping": ("data_import", "validate_mapping"),
        # Expedition
        "process_expedition_request": ("expedition", "process_expedition_request"),
        "verify_expedition_stock": ("expedition", "verify_stock"),
        "confirm_separation": ("expedition", "confirm_separation"),
        "complete_expedition": ("expedition", "complete_expedition"),
        # Reverse
        "process_return": ("reverse", "process_return"),
        "validate_return_origin": ("reverse", "validate_origin"),
        "evaluate_return_condition": ("reverse", "evaluate_condition"),
        # Carrier
        "get_shipping_quotes": ("carrier", "get_quotes"),
        "recommend_carrier": ("carrier", "recommend_carrier"),
        "track_shipment": ("carrier", "track_shipment"),
        # EquipmentResearch
        "research_equipment": ("equipment_research", "research_equipment"),
        "research_equipment_batch": ("equipment_research", "research_batch"),
        "query_equipment_docs": ("equipment_research", "query_equipment_docs"),
        # Observation
        "generate_import_observations": ("observation", "generate_observations"),
    }


# =============================================================================
# Swarm Management (Phase 8)
# =============================================================================


def _get_inventory_swarm():
    """
    Lazy-load the Inventory Swarm.

    Phase 8: Creates and caches a 5-agent Swarm for autonomous import processing.
    The Swarm is shared across all sessions (session state managed separately).
    """
    global _inventory_swarm
    if _inventory_swarm is None:
        from swarm.config import create_inventory_swarm, SwarmConfig

        config = SwarmConfig(
            max_handoffs=30,
            max_iterations=50,
            execution_timeout=1800.0,  # 30 minutes
            node_timeout=300.0,  # 5 minutes per agent
            enable_meta_tooling=True,
        )
        _inventory_swarm = create_inventory_swarm(config)
        logger.info("[Orchestrator] Created Inventory Swarm (Phase 8)")

    return _inventory_swarm


def _get_swarm_session(session_id: str) -> dict:
    """
    Get or create session state for Swarm execution.

    The Swarm maintains state between HIL rounds in _swarm_sessions.
    Each session tracks:
    - context: Accumulated context from previous rounds
    - awaiting_response: Whether waiting for user input
    - questions: Current pending questions
    - import_id: Import transaction ID (after execution)

    Args:
        session_id: Unique session identifier

    Returns:
        Session state dictionary
    """
    if session_id not in _swarm_sessions:
        _swarm_sessions[session_id] = {
            "context": {},
            "awaiting_response": False,
            "questions": [],
            "import_id": None,
            "round_count": 0,
        }
    return _swarm_sessions[session_id]


def _cleanup_swarm_session(session_id: str) -> None:
    """Remove completed session state to prevent memory leaks."""
    if session_id in _swarm_sessions:
        del _swarm_sessions[session_id]
        logger.info(f"[Swarm] Cleaned up session: {session_id}")


async def _invoke_swarm(
    action: str,
    payload: dict,
    user_id: str,
    session_id: str,
) -> dict:
    """
    Invoke the Inventory Swarm for import operations.

    Phase 8: Routes NEXO import actions to the autonomous Swarm.
    Handles multi-round HIL by preserving state between invocations.

    Flow:
    1. First call: Swarm analyzes file, may return questions (stop_action)
    2. Subsequent calls: Resume with user answers until approval
    3. Final call: Execute import with approved mappings

    Args:
        action: NEXO action (analyze_file, submit_answers, execute_import)
        payload: Action-specific parameters
        user_id: User ID for context
        session_id: Session ID for state continuity

    Returns:
        Swarm response with questions or import result
    """
    swarm = _get_inventory_swarm()
    session = _get_swarm_session(session_id)

    logger.info(
        f"[Swarm] Invocation: action={action}, session={session_id}, "
        f"round={session['round_count']}, awaiting={session['awaiting_response']}"
    )

    # Build context for Swarm invocation
    swarm_context = {
        "user_id": user_id,
        "session_id": session_id,
        "action": action,
        **session["context"],  # Include accumulated context
    }

    # Handle different action types
    if action == "nexo_analyze_file":
        # New import - reset session state
        session["context"] = {
            "file_path": payload.get("file_path"),
            "target_table": payload.get("target_table", "inventory_movements"),
            "tenant_id": payload.get("tenant_id", "default"),
        }
        session["round_count"] = 0
        session["awaiting_response"] = False

        prompt = f"""
        Analyze this file for inventory import:
        - File: {payload.get('file_path')}
        - Target table: {payload.get('target_table', 'inventory_movements')}

        Start by analyzing the file structure, then retrieve prior knowledge,
        validate against schema, and generate questions if needed.
        """

    elif action == "nexo_submit_answers":
        # Resume with user answers
        if not session["awaiting_response"]:
            return {
                "success": False,
                "error": "No pending questions for this session",
                "session_id": session_id,
            }

        # Merge user responses into context
        user_responses = payload.get("answers", {})
        session["context"]["user_responses"] = {
            **session["context"].get("user_responses", {}),
            **user_responses,
        }
        session["awaiting_response"] = False

        prompt = f"""
        User has provided answers to clarification questions.

        User responses: {json.dumps(user_responses)}

        Process these answers and either:
        - Generate more questions if needed
        - Proceed to approval request if all mappings confirmed
        """

    elif action == "nexo_execute_import":
        # Execute approved import
        if not session["context"].get("approval_status"):
            return {
                "success": False,
                "error": "Import not approved. User approval required.",
                "session_id": session_id,
            }

        prompt = """
        User has approved the import. Execute the import transaction now.
        Generate audit trail and store learned patterns in memory.
        """

    else:
        # Generic NEXO action - pass through
        prompt = f"Execute NEXO action: {action}\nPayload: {json.dumps(payload)}"

    # Invoke Swarm
    session["round_count"] += 1
    logger.info(f"[Swarm] Starting round {session['round_count']}: {prompt[:100]}...")

    try:
        result = swarm(prompt, **swarm_context)

        # Extract response from Swarm result
        response = _process_swarm_result(result, session)

        # Check for stop_action (HIL pause)
        if response.get("stop_action"):
            session["awaiting_response"] = True
            session["questions"] = response.get("hil_questions", [])
            logger.info(f"[Swarm] HIL pause: {len(session['questions'])} questions")

        # Check for approval status
        if response.get("approval_status") is not None:
            session["context"]["approval_status"] = response["approval_status"]

        # Check for completion
        if response.get("import_id"):
            session["import_id"] = response["import_id"]
            # Keep session for audit, cleanup after configurable time
            logger.info(f"[Swarm] Import complete: {response['import_id']}")

        return {
            "success": True,
            "session_id": session_id,
            "round": session["round_count"],
            **response,
        }

    except Exception as e:
        logger.exception(f"[Swarm] Error in round {session['round_count']}: {e}")
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id,
            "round": session["round_count"],
        }


def _process_swarm_result(result, session: dict) -> dict:
    """
    Process Swarm execution result.

    Extracts relevant information from the Swarm response:
    - stop_action: Whether to pause for HIL
    - hil_questions: Questions for user
    - proposed_mappings: Column mappings
    - import_id: Completed import ID
    - node_history: Agent collaboration sequence
    """
    response = {}

    # Get the final message/response
    if hasattr(result, "message"):
        try:
            response = json.loads(result.message)
        except json.JSONDecodeError:
            response["message"] = result.message

    # Get node history for observability
    if hasattr(result, "node_history"):
        response["agent_sequence"] = [n.node_id for n in result.node_history]

    # Update session context with any new information
    for key in ["file_analysis", "proposed_mappings", "unmapped_columns", "validation_issues"]:
        if key in response:
            session["context"][key] = response[key]

    return response


# =============================================================================
# Swarm Action Mapping (Phase 8)
# =============================================================================

# Actions that route to Swarm when USE_SWARM_IMPORT=true
SWARM_ACTIONS = {
    "nexo_analyze_file",
    "nexo_get_questions",
    "nexo_submit_answers",
    "nexo_execute_import",
    "nexo_learn_from_import",
    "nexo_prepare_processing",
    "nexo_get_prior_knowledge",
    "nexo_get_adaptive_threshold",
}


def _should_use_swarm(action: str) -> bool:
    """Check if action should be routed to Swarm."""
    return USE_SWARM_IMPORT and action in SWARM_ACTIONS


# =============================================================================
# Tools (agents-as-tools pattern)
# =============================================================================


async def _invoke_specialist_internal(
    agent_id: str,
    action: str,
    payload: dict,
    user_id: str = "unknown",
    session_id: str = "default-session",
    request_id: str = "direct-call",
    debug_mode: bool = False,
    agent_name: Optional[str] = None,
) -> dict:
    """
    Internal function to invoke a specialist agent via A2A Protocol.

    This is the core implementation used by both:
    1. The @tool decorated function (called via Strands Agent with ToolContext)
    2. Direct action routing (called without Agent/ToolContext)

    Phase 7.2: Refactored to separate concerns between tool decorator and logic.

    Args:
        agent_id: Target specialist agent ID
        action: Action to perform
        payload: Action-specific parameters
        user_id: User ID for context propagation
        session_id: Session ID for A2A call
        request_id: Request ID for tracing
        debug_mode: Enable debug information in payload
        agent_name: Orchestrator agent name (for debug context)

    Returns:
        Response dict from specialist agent
    """
    client = _get_a2a_client()

    logger.info(
        f"[Orchestrator] Routing to specialist: {agent_id}, action: {action}, "
        f"user_id={user_id}, session_id={session_id}, request_id={request_id}"
    )

    # Build A2A payload with context
    a2a_payload = {
        "action": action,
        "user_id": user_id,  # Propagate user context to specialist
        **payload,
    }

    # Add debug context if enabled
    if debug_mode:
        a2a_payload["_debug"] = {
            "request_id": request_id,
            "orchestrator_agent": agent_name or "orchestrator",
        }

    # Invoke specialist via A2A Protocol
    result = await client.invoke_agent(
        agent_id=agent_id,
        payload=a2a_payload,
        session_id=session_id,
    )

    if not result.success:
        return {
            "success": False,
            "specialist_agent": agent_id,
            "error": result.error or "A2A invocation failed",
            "request_id": request_id,
        }

    # Parse response
    try:
        response_data = json.loads(result.response) if result.response else {}

        # A2A response may wrap result in 'result' field
        if "result" in response_data:
            return {
                "success": True,
                "specialist_agent": agent_id,
                "response": response_data["result"],
                "request_id": request_id,
            }

        # Direct response with success field
        if response_data.get("success") is not None:
            return {
                "success": response_data.get("success", True),
                "specialist_agent": agent_id,
                "response": response_data,
                "request_id": request_id,
            }

        # Non-empty response
        if response_data:
            return {
                "success": True,
                "specialist_agent": agent_id,
                "response": response_data,
                "request_id": request_id,
            }

        # Empty response
        return {
            "success": False,
            "specialist_agent": agent_id,
            "error": "Empty response from specialist agent",
            "request_id": request_id,
        }

    except json.JSONDecodeError:
        # Text response (natural language)
        return {
            "success": True,
            "specialist_agent": agent_id,
            "response": {"message": result.response},
            "request_id": request_id,
        }


@tool(context=True)
async def invoke_specialist(
    agent_id: str,
    action: str,
    payload: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Invoke a specialist agent via A2A Protocol (JSON-RPC 2.0).

    This is the primary routing mechanism for all inventory operations.
    The orchestrator uses this tool to delegate work to specialist agents.

    Phase 7.2 Enhancement: Uses ToolContext for clean state management.
    - user_id, session_id passed via invocation_state (hidden from LLM)
    - tool_use_id for request tracing
    - agent context for observability

    Args:
        agent_id: Target specialist agent. Valid values:
                  estoque_control, intake, nexo_import, learning, validation,
                  reconciliacao, compliance, carrier, expedition, reverse,
                  observation, schema_evolution, equipment_research, data_import
        action: Action to perform on the specialist (e.g., "analyze_file", "create_reservation")
        payload: Action-specific parameters (varies by agent and action)
        tool_context: Strands ToolContext with invocation_state (injected automatically)

    Returns:
        dict with keys:
        - success: boolean
        - specialist_agent: which agent handled the request
        - response: the specialist's response data
        - error: (if failed) error message
        - request_id: tool_use_id for tracing
    """
    # Extract context from invocation_state (Phase 7.2 - clean state management)
    # These are NOT visible to the LLM, only to the tool
    user_id = tool_context.invocation_state.get("user_id", "unknown")
    session_id = tool_context.invocation_state.get("session_id", "default-session")
    debug_mode = tool_context.invocation_state.get("debug", False)
    request_id = tool_context.tool_use.get("toolUseId", "unknown")
    agent_name = tool_context.agent.name if tool_context.agent else None

    # Delegate to internal function
    return await _invoke_specialist_internal(
        agent_id=agent_id,
        action=action,
        payload=payload,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        debug_mode=debug_mode,
        agent_name=agent_name,
    )


@tool
def health_check() -> dict:
    """
    Check orchestrator health status.

    Returns system information including version, deployed commit, available agents,
    and Swarm status (Phase 8).
    """
    discovered_count = len(_tool_provider.discovered_agents) if _tool_provider else 0
    swarm_agents = len(_inventory_swarm.nodes) if _inventory_swarm else 0
    active_sessions = len(_swarm_sessions)

    return {
        "success": True,
        "status": "healthy",
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "version": AGENT_VERSION,
        "git_commit": os.environ.get("GIT_COMMIT_SHA", "unknown"),
        "deployed_at": os.environ.get("DEPLOYED_AT", "unknown"),
        "architecture": "strands_orchestrator_with_swarm",
        "features": {
            "dynamic_discovery": USE_DYNAMIC_DISCOVERY,
            "swarm_import": USE_SWARM_IMPORT,
        },
        "a2a": {
            "discovered_agents": discovered_count,
        },
        "swarm": {
            "enabled": USE_SWARM_IMPORT,
            "agents_count": swarm_agents,
            "agents": ["file_analyst", "schema_validator", "memory_agent", "hil_agent", "import_executor"],
            "active_sessions": active_sessions,
        },
        "specialists": [
            "estoque_control",
            "intake",
            "nexo_import",
            "learning",
            "validation",
            "reconciliacao",
            "compliance",
            "carrier",
            "expedition",
            "reverse",
            "observation",
            "schema_evolution",
            "equipment_research",
            "data_import",
        ],
    }


# =============================================================================
# Orchestrator Factory (Lazy Initialization with Dynamic Discovery)
# =============================================================================


async def _create_orchestrator() -> Agent:
    """
    Create orchestrator with optional dynamic agent discovery.

    Phase 7.1 Enhancement:
    - When USE_DYNAMIC_DISCOVERY=true: Fetch AgentCards and generate dynamic prompt
    - When USE_DYNAMIC_DISCOVERY=false: Use static prompt and mapping

    Returns:
        Configured Strands Agent for orchestration
    """
    global _orchestrator

    if _orchestrator is not None:
        return _orchestrator

    if USE_DYNAMIC_DISCOVERY:
        logger.info("[Orchestrator] Creating with dynamic agent discovery (Phase 7.1)")
        provider = await _get_tool_provider()
        system_prompt = provider.build_system_prompt()
        logger.info("[Orchestrator] Generated dynamic system prompt from discovered agents")
    else:
        logger.info("[Orchestrator] Creating with static configuration")
        system_prompt = DEFAULT_SYSTEM_PROMPT

    _orchestrator = Agent(
        name=AGENT_NAME,
        description="Central orchestrator for Faiston Inventory Management (SGA)",
        model=create_gemini_model("orchestrator"),  # Flash model for speed
        tools=[invoke_specialist, health_check],
        system_prompt=system_prompt,
    )

    return _orchestrator


def _get_orchestrator_sync() -> Agent:
    """
    Get orchestrator synchronously (creates if needed).

    For backward compatibility with sync code paths.
    """
    global _orchestrator

    if _orchestrator is not None:
        return _orchestrator

    # Run async creation in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - create with default prompt
            logger.warning("[Orchestrator] Creating with static config (async context)")
            _orchestrator = Agent(
                name=AGENT_NAME,
                description="Central orchestrator for Faiston Inventory Management (SGA)",
                model=create_gemini_model("orchestrator"),
                tools=[invoke_specialist, health_check],
                system_prompt=DEFAULT_SYSTEM_PROMPT,
            )
        else:
            _orchestrator = loop.run_until_complete(_create_orchestrator())
    except RuntimeError:
        # No event loop - create new one
        _orchestrator = asyncio.run(_create_orchestrator())

    return _orchestrator


# =============================================================================
# BedrockAgentCoreApp Entrypoint
# =============================================================================

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """
    Main entrypoint for AgentCore Runtime.

    Handles requests in three modes:
    1. Natural language (prompt field) → LLM-based routing via orchestrator
    2. Swarm routing (nexo_* actions with USE_SWARM_IMPORT) → 5-agent Swarm
    3. Direct action (action field) → Backward compatibility mapping to specialists

    Phase 7.1: When USE_DYNAMIC_DISCOVERY=true, action mappings are built
    from discovered AgentCard skills.

    Phase 8: When USE_SWARM_IMPORT=true, NEXO import actions are routed
    to the autonomous 5-agent Swarm for multi-round HIL processing.

    Args:
        payload: Request payload
            - prompt: Natural language request for LLM routing
            - action: Direct action name for backward compatibility
            - session_id: Session ID for context
            - Other action-specific parameters

        context: AgentCore context with session_id, identity, etc.

    Returns:
        Response dict from specialist agent, orchestrator, or Swarm
    """
    # Extract parameters
    action = payload.get("action")
    prompt = payload.get("prompt") or payload.get("message")
    session_id = getattr(context, "session_id", None) or payload.get("session_id", "default-session")

    # Extract user identity
    try:
        from shared.identity_utils import extract_user_identity, log_identity_context

        user = extract_user_identity(context, payload)
        user_id = user.user_id
        log_identity_context(user, "SGA-Orchestrator", action or "llm_route", session_id)
    except Exception as e:
        logger.warning(f"[Orchestrator] Identity extraction failed: {e}")
        user_id = payload.get("user_id", "unknown")

    logger.info(
        f"[Orchestrator] action={action}, prompt={prompt[:50] if prompt else None}, "
        f"user_id={user_id}, dynamic_discovery={USE_DYNAMIC_DISCOVERY}, swarm_import={USE_SWARM_IMPORT}"
    )

    try:
        # =================================================================
        # Mode 1: Health Check (special case)
        # =================================================================
        if action == "health_check" or action == "health":
            return health_check()

        # =================================================================
        # Mode 2: Swarm Routing (Phase 8) - NEXO Import Operations
        # =================================================================
        if action and _should_use_swarm(action):
            logger.info(f"[Orchestrator] Swarm routing: {action} → Inventory Swarm")

            # Invoke Swarm for autonomous multi-agent processing
            result = asyncio.run(
                _invoke_swarm(
                    action=action,
                    payload=payload,
                    user_id=user_id,
                    session_id=session_id,
                )
            )
            return result

        # =================================================================
        # Mode 3: Direct Action → Backward Compatibility (A2A)
        # =================================================================
        action_mapping = _get_action_mapping()

        if action and action in action_mapping:
            specialist_id, specialist_action = action_mapping[action]
            logger.info(f"[Orchestrator] Direct routing: {action} → {specialist_id}/{specialist_action}")

            # Use internal function directly (no ToolContext needed)
            # Phase 7.2: Pass context explicitly for direct action calls
            result = asyncio.run(
                _invoke_specialist_internal(
                    agent_id=specialist_id,
                    action=specialist_action,
                    payload=payload,
                    user_id=user_id,
                    session_id=session_id,
                    request_id=f"direct-{action}",  # Distinguish from LLM-routed calls
                    debug_mode=False,
                )
            )
            return result

        # =================================================================
        # Mode 3: Natural Language → LLM-based Routing
        # =================================================================
        if prompt:
            logger.info(f"[Orchestrator] LLM routing: {prompt[:100]}...")

            # Get or create orchestrator
            orchestrator = _get_orchestrator_sync()

            # Build prompt for LLM (visible context)
            context_info = f"""
Request: {prompt}
"""
            # Let the orchestrator Agent decide routing
            # Phase 7.2: Pass user context via invocation_state (hidden from LLM)
            result = orchestrator(
                context_info,
                user_id=user_id,           # Hidden from LLM, available to tools
                session_id=session_id,     # Hidden from LLM, available to tools
                debug=False,               # Enable for verbose logging
            )

            # Extract the response
            if hasattr(result, "message"):
                try:
                    return json.loads(result.message)
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "response": result.message,
                        "agent_id": AGENT_ID,
                    }
            return {
                "success": True,
                "response": str(result),
                "agent_id": AGENT_ID,
            }

        # =================================================================
        # Mode 4: Unknown Action → Fallback to Legacy Handler
        # =================================================================
        if action:
            logger.warning(f"[Orchestrator] Unknown action: {action}, attempting legacy fallback")

            # Try to import and call legacy handler from backup
            try:
                import importlib.util

                backup_path = os.path.join(os.path.dirname(__file__), "main.py.backup")

                if os.path.exists(backup_path):
                    spec = importlib.util.spec_from_file_location("legacy_main", backup_path)
                    legacy = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(legacy)

                    # Call legacy invoke
                    return legacy.invoke(payload, context)
            except Exception as e:
                logger.error(f"[Orchestrator] Legacy fallback failed: {e}")

            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "hint": "Use 'prompt' field for natural language or check available actions",
            }

        # =================================================================
        # No action or prompt provided
        # =================================================================
        return {
            "success": False,
            "error": "Missing 'action' or 'prompt' in request",
            "usage": {
                "prompt": "Natural language request for LLM routing",
                "action": "Direct action name (e.g., 'nexo_analyze_file')",
            },
        }

    except Exception as e:
        logger.exception(f"[Orchestrator] Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "agent_id": AGENT_ID,
        }


# =============================================================================
# Main (for local testing)
# =============================================================================

if __name__ == "__main__":
    app.run()
