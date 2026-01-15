# =============================================================================
# Faiston Inventory Orchestrator Agent (ADR-002 Architecture)
# =============================================================================
# This is a STRANDS AGENT, not a Python wrapper of agents.
#
# ARCHITECTURE PRINCIPLES (per ADR-002):
# 1. Orchestrators ARE Agents - Full Strands Agent with hooks, session, output
# 2. Specialists at Same Level - All agents are peers, not parent-child
# 3. No Routing Tables in Prompts - LLM decides based on tool descriptions
# 4. AgentCoreMemorySessionManager - Persistent session state
#
# ROUTING:
# - LLM (Gemini Flash) decides which specialist to invoke based on intent
# - The invoke_specialist tool describes each agent's capabilities
# - No hardcoded ACTION_TO_SPECIALIST mapping (breaking change per ADR-002)
#
# MODES:
# 1. Health Check → System status
# 2. Swarm (nexo_*) → Autonomous 5-agent Swarm for imports
# 2.5. Infrastructure → Deterministic routing for pure infra ops (S3 URLs)
# 3. LLM-based Routing → Natural language + business data queries (100% Agentic)
#
# Reference:
# - https://strandsagents.com/latest/
# - docs/adr/ADR-002-faiston-agent-ecosystem.md
# =============================================================================

import asyncio
import json
import logging
import os
from typing import Optional

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool, ToolContext

# Agent utilities
from agents.utils import create_gemini_model, AGENT_VERSION, extract_json

# Configuration
from config.agent_urls import RUNTIME_IDS, get_agent_url

# Direct tool imports for Infrastructure Actions (bypass A2A for deterministic ops)
# NOTE: Import is done lazily in _handle_infrastructure_action() to avoid circular deps

# Hooks (Phase 1 ADR-002)
from shared.hooks.logging_hook import LoggingHook
from shared.hooks.metrics_hook import MetricsHook
from shared.hooks.guardrails_hook import GuardrailsHook

# Swarm response extraction (BUG-020)
# BUG-020 v5: Use _process_swarm_result() for 100% Strands-compliant extraction
from swarm.response_utils import (
    _extract_tool_output_from_swarm_result,
    _process_swarm_result,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "inventory_management"
AGENT_NAME = "FaistonInventoryOrchestrator"
AGENT_DESCRIPTION = """
Intelligent orchestrator for Faiston Inventory Management (SGA).
Routes requests to specialist agents based on user intent.
Uses LLM reasoning to select the appropriate specialist.
"""

# =============================================================================
# System Prompt (No Routing Tables - LLM Decides from Tool Descriptions)
# =============================================================================

SYSTEM_PROMPT = """
# Faiston Inventory Management Orchestrator

You are the central intelligence for the SGA (Sistema de Gestao de Ativos).
Your role is to understand user requests and delegate to the appropriate specialist agent.

## Your Workflow

1. **Understand**: Analyze the user's intent from their message
2. **Select**: Choose the right specialist agent using the invoke_specialist tool
3. **Invoke**: Call the specialist with appropriate action and payload
4. **Return**: Provide the specialist's response to the user

## Decision Making

You have access to 15+ specialist agents. Each invocation of invoke_specialist
requires you to specify:
- agent_id: Which specialist handles this domain
- action: What operation to perform
- payload: Parameters for the operation

The tool description tells you what each agent does. Trust your reasoning.

## Response Format

Always return structured JSON responses with:
- success: boolean
- specialist_agent: which agent handled the request
- response: the actual result data
- error: (if failed) error message

## Important

- Do NOT ask the user which agent to use - decide based on context
- Do NOT list agents to the user - just route to the right one
- Focus on UNDERSTANDING the request, not on explaining your routing
"""

# =============================================================================
# Swarm Configuration (Phase 8)
# =============================================================================

USE_SWARM_IMPORT = os.environ.get("USE_SWARM_IMPORT", "true").lower() == "true"

# Actions routed to Swarm when USE_SWARM_IMPORT=true
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

# =============================================================================
# Infrastructure Actions (Deterministic Routing - No LLM Needed)
# =============================================================================
#
# IMPORTANT: Only INFRASTRUCTURE operations go here!
# ALL business data queries MUST use LLM → A2A → MCP Gateway → DB
# This maintains the 100% Agentic AI principle for business logic.
#
# Infrastructure ops are pure technical operations (S3 URLs, health checks)
# that don't require LLM reasoning but DO need specialist agent execution.
#
INFRASTRUCTURE_ACTIONS = {
    # S3 presigned URLs (pure infrastructure, no business logic)
    "get_nf_upload_url": ("intake", "get_upload_url"),
    "get_presigned_download_url": ("intake", "get_download_url"),
}


def _handle_infrastructure_action(action: str, payload: dict) -> dict:
    """
    Handle infrastructure actions directly without A2A protocol.

    BUG-017 FIX: A2A calls pass through the specialist's LLM which wraps
    the tool result in conversational text. For infrastructure operations
    like S3 presigned URLs, we need raw JSON responses.

    This function imports and calls the tool functions directly, bypassing
    the A2A protocol entirely for deterministic infrastructure operations.

    Args:
        action: Infrastructure action name (from INFRASTRUCTURE_ACTIONS)
        payload: Action parameters (filename, content_type, etc.)

    Returns:
        Raw JSON response dict (not LLM-wrapped)
    """
    # Lazy import to avoid circular dependencies
    from tools.s3_client import SGAS3Client

    try:
        if action == "get_nf_upload_url":
            # Generate presigned upload URL for NF document
            filename = payload.get("filename", "document")
            content_type = payload.get("content_type", "application/octet-stream")

            s3 = SGAS3Client()
            key = s3.get_temp_path(filename)
            url_info = s3.generate_upload_url(
                key=key, content_type=content_type, expires_in=3600
            )

            # Rename 'key' to 's3_key' for API consistency (as intake agent does)
            url_info["s3_key"] = url_info.pop("key", key)

            logger.info(
                f"[Infrastructure] Generated upload URL for {filename}: {key}"
            )
            return {
                "success": True,
                "specialist_agent": "intake",
                "response": url_info,
            }

        elif action == "get_presigned_download_url":
            # Generate presigned download URL for existing S3 object
            s3_key = payload.get("s3_key") or payload.get("key")
            if not s3_key:
                return {
                    "success": False,
                    "error": "Missing 's3_key' parameter",
                }

            s3 = SGAS3Client()
            url_info = s3.generate_download_url(key=s3_key, expires_in=3600)

            logger.info(f"[Infrastructure] Generated download URL for {s3_key}")
            return {
                "success": True,
                "specialist_agent": "intake",
                "response": url_info,
            }

        else:
            # Unknown infrastructure action (shouldn't happen)
            return {
                "success": False,
                "error": f"Unknown infrastructure action: {action}",
            }

    except Exception as e:
        logger.exception(f"[Infrastructure] Error handling {action}: {e}")
        return {
            "success": False,
            "error": str(e),
            "action": action,
        }


# Lazy-loaded Swarm instance
_inventory_swarm = None
_swarm_sessions = {}  # session_id -> session state


# =============================================================================
# Specialist Invocation Tool
# =============================================================================


def _build_agent_runtime_arn(agent_id: str) -> Optional[str]:
    """Build AgentCore runtime ARN from agent ID."""
    runtime_id = RUNTIME_IDS.get(agent_id)
    if not runtime_id:
        return None

    region = os.environ.get("AWS_REGION", "us-east-2")
    account_id = os.environ.get("AWS_ACCOUNT_ID", "377311924364")
    return f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/{runtime_id}"


async def _invoke_agent_via_a2a(
    agent_id: str,
    action: str,
    payload: dict,
    session_id: str,
    user_id: str,
) -> dict:
    """
    Invoke a specialist agent via A2A Protocol (boto3 SDK).

    Uses AWS Bedrock AgentCore invoke_agent_runtime API with SigV4 authentication.
    The boto3 SDK handles IAM role credentials correctly from inside AgentCore.

    Args:
        agent_id: Target specialist agent ID
        action: Action to perform
        payload: Action parameters
        session_id: Session ID for context
        user_id: User ID for context propagation

    Returns:
        Response dict from specialist
    """
    import uuid
    import boto3
    from botocore.config import Config

    runtime_arn = _build_agent_runtime_arn(agent_id)
    if not runtime_arn:
        return {
            "success": False,
            "error": f"Unknown agent: {agent_id}",
            "available_agents": list(RUNTIME_IDS.keys()),
        }

    # Build A2A JSON-RPC 2.0 request
    message_id = str(uuid.uuid4())
    a2a_request = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": json.dumps({
                            "action": action,
                            "user_id": user_id,
                            **payload,
                        }),
                    }
                ],
                "messageId": message_id,
            }
        },
    }

    try:
        # boto3 client with adaptive retry
        config = Config(
            connect_timeout=300,
            read_timeout=300,
            retries={"max_attempts": 5, "mode": "adaptive"},
        )
        client = boto3.client(
            "bedrock-agentcore",
            region_name=os.environ.get("AWS_REGION", "us-east-2"),
            config=config,
        )

        logger.info(f"[Orchestrator] Invoking {agent_id} via A2A: action={action}")

        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=json.dumps(a2a_request).encode("utf-8"),
        )

        # Read response body (StreamingBody)
        response_body_stream = response.get("response")
        if response_body_stream:
            response_body = response_body_stream.read().decode("utf-8")
            response_data = json.loads(response_body)

            # Extract response from JSON-RPC result
            result = response_data.get("result", {})
            message = result.get("message", {})
            parts = message.get("parts", [])

            # Try message parts first
            response_text = ""
            for part in parts:
                if part.get("kind") == "text":
                    response_text += part.get("text", "")

            # Try artifacts if no message parts
            if not response_text:
                for artifact in result.get("artifacts", []):
                    for part in artifact.get("parts", []):
                        if part.get("kind") == "text":
                            response_text = part.get("text", "")
                            break

            # Parse the response
            if response_text:
                try:
                    # Handle both dict (already parsed) and string (needs parsing)
                    if isinstance(response_text, dict):
                        parsed = response_text
                        logger.debug("[A2A] response_text already dict, using directly")
                    else:
                        # Strip markdown code blocks before parsing (LLM may wrap JSON)
                        clean_text = extract_json(response_text)
                        parsed = json.loads(clean_text)
                        logger.debug("[A2A] Parsed JSON from response_text (markdown stripped)")
                    return {
                        "success": parsed.get("success", True),
                        "specialist_agent": agent_id,
                        "response": parsed,
                    }
                except (json.JSONDecodeError, TypeError):
                    return {
                        "success": True,
                        "specialist_agent": agent_id,
                        "response": {"message": response_text},
                    }

        return {
            "success": False,
            "specialist_agent": agent_id,
            "error": "Empty response from specialist",
        }

    except Exception as e:
        logger.exception(f"[Orchestrator] A2A invocation error: {e}")
        return {
            "success": False,
            "specialist_agent": agent_id,
            "error": str(e),
        }


@tool(context=True)
async def invoke_specialist(
    agent_id: str,
    action: str,
    payload: dict,
    tool_context: ToolContext,
) -> dict:
    """
    Invoke a specialist agent to handle a specific task.

    This is the primary routing mechanism. Select the appropriate agent
    based on the user's request and the agent capabilities below.

    ## Available Specialist Agents:

    ### estoque_control
    Inventory control operations: stock movements, reservations, expeditions,
    transfers, returns, balance queries, asset location tracking.
    Actions: query_balance, create_reservation, cancel_reservation, create_movement,
    process_expedition, create_transfer, query_asset_location

    ### intake
    Document intake and processing: NF (Nota Fiscal) PDF/XML extraction,
    OCR scanning, invoice validation, entry confirmation.
    Actions: process_nf, validate_extraction, confirm_entry, parse_nf_image, get_upload_url

    ### nexo_import
    Smart file import with AI analysis: CSV, XLSX, PDF file analysis,
    column mapping, schema inference, iterative HIL dialogue.
    Actions: analyze_file, get_questions, submit_answers, execute_import

    ### learning
    Memory and pattern learning: prior knowledge retrieval, import pattern
    storage, adaptive thresholds, historical analysis.
    Actions: retrieve_prior_knowledge, store_pattern, get_adaptive_threshold

    ### validation
    Data validation: schema validation, type checking, constraint verification,
    business rule validation.
    Actions: validate_data, validate_schema, check_constraints

    ### reconciliacao
    Inventory reconciliation: counting campaigns, divergence analysis,
    adjustment proposals, physical vs system comparison.
    Actions: start_campaign, submit_count, analyze_divergences, propose_adjustment

    ### compliance
    Policy and approval workflows: HIL approvals, policy validation,
    audit trail, authorization checks.
    Actions: request_approval, validate_policy, check_authorization

    ### carrier
    Shipping and logistics: carrier quotes, recommendations, shipment tracking,
    delivery scheduling.
    Actions: get_quotes, recommend_carrier, track_shipment

    ### expedition
    Outbound logistics: expedition processing, stock verification,
    separation confirmation, SAP export.
    Actions: process_expedition_request, verify_stock, confirm_separation, complete_expedition

    ### reverse
    Reverse logistics: return processing, condition evaluation,
    origin validation, restocking decisions.
    Actions: process_return, validate_origin, evaluate_condition

    ### observation
    Audit and observations: import observations, audit logging,
    analysis notes, traceability records.
    Actions: generate_observations, log_audit_event

    ### schema_evolution
    Schema management: column type inference, schema changes,
    migration planning, compatibility checks.
    Actions: infer_column_types, propose_schema_change

    ### equipment_research
    Equipment documentation: datasheet lookup, specifications,
    compatibility research, vendor information.
    Actions: research_equipment, research_batch, query_equipment_docs

    ### data_import
    Generic data import: bulk imports, SAP imports, preview mode,
    mapping validation.
    Actions: preview_import, execute_import, execute_sap_import

    ### enrichment
    Data enrichment: equipment specs via Tavily AI search,
    part number validation, knowledge base sync.
    Actions: enrich_equipment, enrich_batch, validate_part_number, sync_knowledge_base

    Args:
        agent_id: ID of the specialist agent to invoke
        action: Action to perform on the specialist
        payload: Parameters for the action (varies by agent)
        tool_context: Strands ToolContext (injected automatically)

    Returns:
        Dict with success status, specialist_agent, and response data
    """
    # Extract context from invocation_state (hidden from LLM)
    user_id = tool_context.invocation_state.get("user_id", "unknown")
    session_id = tool_context.invocation_state.get("session_id", "default-session")
    request_id = tool_context.tool_use.get("toolUseId", "unknown")

    logger.info(
        f"[Orchestrator] Routing: agent={agent_id}, action={action}, "
        f"user={user_id}, session={session_id}, request={request_id}"
    )

    result = await _invoke_agent_via_a2a(
        agent_id=agent_id,
        action=action,
        payload=payload,
        session_id=session_id,
        user_id=user_id,
    )

    result["request_id"] = request_id
    return result


@tool
def health_check() -> dict:
    """
    Check orchestrator health status.

    Returns system information including version, architecture type,
    available specialist agents, and Swarm status.
    """
    return {
        "success": True,
        "status": "healthy",
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "version": AGENT_VERSION,
        "git_commit": os.environ.get("GIT_COMMIT_SHA", "unknown"),
        "deployed_at": os.environ.get("DEPLOYED_AT", "unknown"),
        "architecture": "adr-002-strands-orchestrator",
        "features": {
            "swarm_import": USE_SWARM_IMPORT,
            "hooks_enabled": True,
        },
        "swarm": {
            "enabled": USE_SWARM_IMPORT,
            "agents": [
                "file_analyst",
                "schema_validator",
                "memory_agent",
                "hil_agent",
                "import_executor",
            ],
            "active_sessions": len(_swarm_sessions),
        },
        "specialists": list(RUNTIME_IDS.keys()),
    }


# =============================================================================
# Swarm Integration (Phase 8 - Kept from original)
# =============================================================================


def _get_inventory_swarm():
    """Lazy-load the Inventory Swarm."""
    global _inventory_swarm
    if _inventory_swarm is None:
        from swarm.config import create_inventory_swarm, SwarmConfig

        config = SwarmConfig(
            max_handoffs=30,
            max_iterations=50,
            execution_timeout=1800.0,
            node_timeout=300.0,
            enable_meta_tooling=True,
        )
        _inventory_swarm = create_inventory_swarm(config)
        logger.info("[Orchestrator] Created Inventory Swarm")

    return _inventory_swarm


def _get_swarm_session(session_id: str) -> dict:
    """Get or create session state for Swarm execution."""
    if session_id not in _swarm_sessions:
        _swarm_sessions[session_id] = {
            "context": {},
            "awaiting_response": False,
            "questions": [],
            "import_id": None,
            "round_count": 0,
        }
    return _swarm_sessions[session_id]


async def _invoke_swarm(
    action: str,
    payload: dict,
    user_id: str,
    session_id: str,
) -> dict:
    """
    Invoke the Inventory Swarm for NEXO import operations.

    The Swarm handles autonomous multi-agent processing with HIL support.
    """
    swarm = _get_inventory_swarm()
    session = _get_swarm_session(session_id)

    logger.info(
        f"[Swarm] Invocation: action={action}, session={session_id}, "
        f"round={session['round_count']}"
    )

    # Build Swarm context
    swarm_context = {
        "user_id": user_id,
        "session_id": session_id,
        "action": action,
        **session["context"],
    }

    # Build prompt based on action
    if action == "nexo_analyze_file":
        s3_key = payload.get("s3_key") or payload.get("file_path") or payload.get("key", "")
        filename = payload.get("filename", "")

        session["context"] = {
            "s3_key": s3_key,
            "filename": filename,
            "target_table": payload.get("target_table", "inventory_movements"),
            "tenant_id": payload.get("tenant_id", "default"),
        }
        session["round_count"] = 0

        prompt = f"""
        Analyze this file for inventory import using the unified_analyze_file tool.
        - s3_key: "{s3_key}"
        - filename: "{filename}"
        - session_id: "{session_id}"
        Return the tool's response directly as JSON.
        """

    elif action == "nexo_submit_answers":
        if not session["awaiting_response"]:
            return {
                "success": False,
                "error": "No pending questions for this session",
                "session_id": session_id,
            }

        user_responses = payload.get("answers", {})
        session["context"]["user_responses"] = {
            **session["context"].get("user_responses", {}),
            **user_responses,
        }
        session["awaiting_response"] = False

        s3_key = session["context"].get("s3_key", "")
        analysis_round = session.get("round_count", 1) + 1

        prompt = f"""
        User provided answers. Re-analyze with:
        - s3_key: "{s3_key}"
        - session_id: "{session_id}"
        - user_responses: {json.dumps(user_responses)}
        - analysis_round: {analysis_round}
        """

    elif action == "nexo_execute_import":
        if not session["context"].get("approval_status"):
            return {
                "success": False,
                "error": "Import not approved. User approval required.",
                "session_id": session_id,
            }

        prompt = "Execute the approved import and generate audit trail."

    else:
        prompt = f"Execute NEXO action: {action}\nPayload: {json.dumps(payload)}"

    # Invoke Swarm
    session["round_count"] += 1

    try:
        result = swarm(prompt, **swarm_context)

        # BUG-020 v3: Log Swarm result structure for debugging
        logger.info(
            "[Swarm] Result structure: results_keys=%s, status=%s, has_message=%s",
            list(result.results.keys()) if hasattr(result, "results") and result.results else "None",
            getattr(result, "status", "N/A"),
            bool(getattr(result, "message", None)),
        )

        # =====================================================================
        # BUG-020 v5 FIX: 100% Strands-Compliant Response Extraction
        # =====================================================================
        # Uses _process_swarm_result() which contains ALL v4 fixes and uses
        # ONLY official Strands patterns:
        # - result.results["agent_name"].result (official)
        # - result.status (official)
        # - result.entry_point.messages (fallback for tool_result blocks)
        #
        # REMOVED: result.message fallback (NOT a valid Strands attribute!)
        # =====================================================================
        response = _process_swarm_result(
            swarm_result=result,
            session=session,
            action="nexo_analyze_file"
        )

        logger.debug(
            "[Swarm] Processed response: success=%s, has_analysis=%s",
            response.get("success"),
            "analysis" in response,
        )

        # Strands-compliant error handling using result.status (official attribute)
        if not response.get("success") or getattr(result, "status", None) == "error":
            logger.warning(
                "[Swarm] Extraction failed or error status, status=%s",
                getattr(result, "status", "unknown"),
            )
            # Return structured error with HIL question (agentic behavior, not try/catch)
            return {
                "success": False,
                "session_id": session_id,
                "round": session["round_count"],
                "error": "Swarm extraction failed",
                "questions": [{
                    "id": "swarm_extraction_error",
                    "question": "Não foi possível processar o arquivo. Por favor, tente novamente.",
                    "type": "error"
                }],
                "analysis": {
                    "sheets": [],
                    "sheet_count": 0,
                    "total_rows": 0,
                    "recommended_strategy": "manual_review"
                }
            }

        # Check for HIL pause (from _process_swarm_result context update)
        if response.get("stop_action") or session.get("awaiting_response"):
            session["awaiting_response"] = True
            session["questions"] = response.get("questions", [])

        # Check approval status
        if response.get("approval_status") is not None:
            session["context"]["approval_status"] = response["approval_status"]

        # Check completion
        if response.get("import_id"):
            session["import_id"] = response["import_id"]

        # Add session metadata to the processed response
        response["session_id"] = session_id
        response["round"] = session["round_count"]

        return response

    except Exception as e:
        logger.exception(f"[Swarm] Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id,
            "round": session["round_count"],
        }


# =============================================================================
# Orchestrator Factory
# =============================================================================


def create_orchestrator() -> Agent:
    """
    Create the Inventory Orchestrator as a full Strands Agent.

    This is NOT a Python wrapper - it's a proper Strands Agent with:
    - AgentCoreMemorySessionManager (future)
    - HookProvider implementations for logging, metrics, guardrails
    - Structured output capability
    - LLM-based routing (no hardcoded tables)
    """
    # Feature: Guardrails in shadow mode
    guardrail_id = os.environ.get("GUARDRAIL_ID")

    hooks = [
        LoggingHook(log_level=logging.INFO),
        MetricsHook(namespace="FaistonSGA", emit_to_cloudwatch=True),
    ]

    if guardrail_id:
        hooks.append(GuardrailsHook(guardrail_id=guardrail_id, shadow_mode=True))

    orchestrator = Agent(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=create_gemini_model("orchestrator"),  # Gemini Flash for speed
        tools=[invoke_specialist, health_check],
        system_prompt=SYSTEM_PROMPT,
        hooks=hooks,
    )

    logger.info(f"[Orchestrator] Created {AGENT_NAME} with {len(hooks)} hooks")
    return orchestrator


# =============================================================================
# BedrockAgentCoreApp Entrypoint
# =============================================================================

app = BedrockAgentCoreApp()

# Cached orchestrator instance
_orchestrator = None


def _get_orchestrator() -> Agent:
    """Get or create the orchestrator agent."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator()
    return _orchestrator


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """
    Main entrypoint for AgentCore Runtime.

    Routing Modes:
    1. Health check → Direct response
    2. NEXO Swarm actions → Autonomous 5-agent Swarm
    2.5. Infrastructure actions → Deterministic routing for pure infra (S3 URLs)
    3. Natural language or action → LLM-based routing (100% Agentic)

    IMPORTANT: Business data queries (query_balance, query_asset_location, etc.)
    MUST go through Mode 3 (LLM) to maintain 100% Agentic AI principle.
    Only pure infrastructure ops (S3 URLs) bypass LLM via Mode 2.5.

    Args:
        payload: Request with either:
            - prompt: Natural language request
            - action: Direct action name (for Swarm/Infrastructure)
        context: AgentCore context with session_id, identity

    Returns:
        Response from orchestrator, specialist, or Swarm
    """
    action = payload.get("action")
    prompt = payload.get("prompt") or payload.get("message")
    session_id = getattr(context, "session_id", None) or payload.get("session_id", "default-session")

    # Extract user identity
    try:
        from shared.identity_utils import extract_user_identity

        user = extract_user_identity(context, payload)
        user_id = user.user_id
    except Exception as e:
        logger.warning(f"[Orchestrator] Identity extraction failed: {e}")
        user_id = payload.get("user_id", "unknown")

    logger.info(
        f"[Orchestrator] Request: action={action}, prompt={prompt[:50] if prompt else None}, "
        f"user={user_id}, session={session_id}"
    )

    try:
        # Mode 1: Health Check
        if action in ("health_check", "health"):
            return health_check()

        # Mode 2: Swarm Routing (NEXO imports)
        if action and USE_SWARM_IMPORT and action in SWARM_ACTIONS:
            logger.info(f"[Orchestrator] Swarm routing: {action}")
            return asyncio.run(
                _invoke_swarm(
                    action=action,
                    payload=payload,
                    user_id=user_id,
                    session_id=session_id,
                )
            )

        # Mode 2.5: Infrastructure Actions (DIRECT TOOL CALL - No A2A)
        # BUG-017 FIX: A2A calls pass through specialist's LLM which wraps
        # responses in conversational text. For infrastructure ops like S3
        # presigned URLs, we call the tool functions directly for raw JSON.
        #
        # NOTE: Only S3/infrastructure ops - business data MUST go through LLM
        # This preserves the 100% Agentic AI principle for all business logic.
        if action and action in INFRASTRUCTURE_ACTIONS:
            logger.info(f"[Orchestrator] Infrastructure direct call: {action}")
            return _handle_infrastructure_action(action=action, payload=payload)

        # Mode 3: LLM-based Routing (Natural Language or Direct Action)
        orchestrator = _get_orchestrator()

        # Build the prompt for the LLM
        if prompt:
            llm_prompt = prompt
        elif action:
            # Convert action to natural language for LLM routing
            llm_prompt = f"Execute the '{action}' operation with these parameters: {json.dumps(payload)}"
        else:
            return {
                "success": False,
                "error": "Missing 'action' or 'prompt' in request",
                "usage": {
                    "prompt": "Natural language request",
                    "action": "Action name (nexo_analyze_file, etc.)",
                },
            }

        logger.info(f"[Orchestrator] LLM routing: {llm_prompt[:100]}...")

        # Invoke orchestrator with context in invocation_state
        result = orchestrator(
            llm_prompt,
            user_id=user_id,  # Hidden from LLM, available to tools
            session_id=session_id,  # Hidden from LLM, available to tools
        )

        # Extract response
        if hasattr(result, "message"):
            try:
                # Handle both dict (already parsed) and string (needs parsing)
                if isinstance(result.message, dict):
                    return result.message
                # Strip markdown code blocks before parsing (LLM may wrap JSON)
                clean_message = extract_json(result.message)
                return json.loads(clean_message)
            except (json.JSONDecodeError, TypeError):
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

    except Exception as e:
        logger.exception(f"[Orchestrator] Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "agent_id": AGENT_ID,
        }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "app",
    "create_orchestrator",
    "invoke",
    "AGENT_ID",
    "AGENT_NAME",
]


# =============================================================================
# Main (for local testing)
# =============================================================================

if __name__ == "__main__":
    app.run()
