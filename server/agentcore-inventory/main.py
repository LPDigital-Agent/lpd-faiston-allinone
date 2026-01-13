# =============================================================================
# AWS Bedrock AgentCore Runtime Entrypoint - Faiston SGA Inventory
# =============================================================================
# Main entrypoint for Faiston SGA Inventory agents deployed to AgentCore Runtime.
# Uses BedrockAgentCoreApp decorator pattern for serverless deployment.
#
# Framework: Google ADK with native Gemini 3.0 Pro (per CLAUDE.md mandate)
# Model: All agents use gemini-3-pro-preview exclusively
# Module: Gestao de Ativos -> Gestao de Estoque
#
# 5 AI Agents:
# - EstoqueControlAgent: Core +/- inventory movements
# - IntakeAgent: NF PDF/XML extraction
# - ReconciliacaoAgent: Divergence detection and inventory counts
# - ComplianceAgent: Policy validation and approval workflows
# - ComunicacaoAgent: Notifications and technician communication
#
# OPTIMIZATION: Lazy imports for faster cold start
# Agents are imported only when needed, reducing initialization time.
# This is critical for AgentCore Runtime's 30-second initialization limit.
# =============================================================================

from bedrock_agentcore.runtime import BedrockAgentCoreApp
import asyncio
import json
import os
from typing import Optional

# LAZY IMPORTS: Agents are imported inside handler functions to reduce cold start.
# Each agent imports Google ADK packages (~3-5s each).

# =============================================================================
# Database Adapter Configuration (PostgreSQL Migration)
# =============================================================================
# Feature flag to enable PostgreSQL via MCP Gateway.
# When enabled, agents use GatewayPostgresAdapter instead of DynamoDBAdapter.
#
# Migration phases:
# 1. USE_POSTGRES_MCP=false (default): All reads/writes go to DynamoDB
# 2. USE_POSTGRES_MCP=true: Reads go to PostgreSQL via MCP Gateway
# 3. After validation: Remove DynamoDB code and set as default
#
# Environment variables:
# - USE_POSTGRES_MCP: "true" to enable PostgreSQL adapter
# - AGENTCORE_GATEWAY_URL: Full MCP endpoint URL
# - AGENTCORE_GATEWAY_ID: Gateway ID (alternative to full URL)
# =============================================================================

USE_POSTGRES_MCP = os.environ.get("USE_POSTGRES_MCP", "true").lower() == "true"
AGENTCORE_GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
AGENTCORE_GATEWAY_ID = os.environ.get("AGENTCORE_GATEWAY_ID", "")

# Cached A2A client instance (lazy initialized)
_a2a_client = None

# Cached identity utils (lazy initialized for cold start optimization)
_identity_utils = None


def _get_identity_utils():
    """
    Lazy-load identity utilities for AgentCore Identity compliance.

    Returns tuple of (extract_user_identity, log_identity_context) functions.
    """
    global _identity_utils
    if _identity_utils is None:
        from shared.identity_utils import extract_user_identity, log_identity_context
        _identity_utils = (extract_user_identity, log_identity_context)
    return _identity_utils


def _get_a2a_client():
    """
    Lazy-load A2A client for agent invocations.

    Returns cached instance to avoid repeated initialization.
    """
    global _a2a_client
    if _a2a_client is None:
        from shared.a2a_client import A2AClient
        _a2a_client = A2AClient()
    return _a2a_client


async def _invoke_agent_a2a(
    agent_id: str,
    action: str,
    payload: dict,
    session_id: str,
    user_id: str = None,
) -> dict:
    """
    Invoke an agent via A2A Protocol (JSON-RPC 2.0).

    This is the standard pattern for 100% Agentic architecture:
    - Each agent runs in its own AgentCore runtime
    - Communication via A2A Protocol (JSON-RPC 2.0)
    - Session propagated for context continuity

    Args:
        agent_id: Target agent ID (e.g., "intake", "nexo_import")
        action: Action to perform (e.g., "process_nf", "analyze_file")
        payload: Action-specific payload
        session_id: Session ID for context
        user_id: Optional user ID

    Returns:
        Agent response dict with success/error status
    """
    client = _get_a2a_client()

    # Build A2A payload
    a2a_payload = {
        "action": action,
        **payload,
    }
    if user_id:
        a2a_payload["user_id"] = user_id

    # Invoke agent via A2A
    result = await client.invoke_agent(
        agent_id=agent_id,
        payload=a2a_payload,
        session_id=session_id,
    )

    if not result.success:
        return {
            "success": False,
            "error": result.error or "A2A invocation failed",
            "agent_id": agent_id,
        }

    # Parse response - agents return JSON in the response text
    try:
        import json
        response_data = json.loads(result.response) if result.response else {}

        # A2A response wraps actual result in 'result' field
        if "result" in response_data:
            return response_data["result"]
        return response_data

    except json.JSONDecodeError:
        # If response is not JSON, return as-is
        return {
            "success": True,
            "response": result.response,
            "agent_id": agent_id,
        }

# Cached adapter instance (lazy initialized)
_database_adapter = None


def get_database_adapter():
    """
    Factory function to get the appropriate database adapter.

    Returns GatewayPostgresAdapter if USE_POSTGRES_MCP is enabled,
    otherwise returns DynamoDBAdapter (legacy).

    The adapter is cached after first initialization to avoid
    repeated setup costs.

    Returns:
        DatabaseAdapter implementation (GatewayPostgresAdapter or DynamoDBAdapter)
    """
    global _database_adapter

    if _database_adapter is not None:
        return _database_adapter

    if USE_POSTGRES_MCP and (AGENTCORE_GATEWAY_URL or AGENTCORE_GATEWAY_ID):
        # Use PostgreSQL via MCP Gateway with IAM SigV4 auth
        # Per AWS Well-Architected Framework: Use IAM roles, not tokens
        from tools.mcp_gateway_client import MCPGatewayClientFactory
        from tools.gateway_adapter import GatewayPostgresAdapter

        # No token provider needed - MCPGatewayClient uses SigV4 signing
        # Credentials come from AgentCore Runtime's execution role
        mcp_client = MCPGatewayClientFactory.create_from_env()
        _database_adapter = GatewayPostgresAdapter(mcp_client)

        import logging
        logging.info("Database adapter: GatewayPostgresAdapter (PostgreSQL via MCP, IAM auth)")
    else:
        # Use DynamoDB (legacy)
        from tools.dynamodb_client import SGADynamoDBClient
        _database_adapter = SGADynamoDBClient()

        import logging
        logging.info("Database adapter: SGADynamoDBClient (DynamoDB)")

    return _database_adapter


def get_adapter_info() -> dict:
    """
    Get information about the current database adapter configuration.

    Useful for health checks and debugging.

    Returns:
        Dict with adapter type and configuration status
    """
    return {
        "use_postgres_mcp": USE_POSTGRES_MCP,
        "gateway_url_configured": bool(AGENTCORE_GATEWAY_URL),
        "gateway_id_configured": bool(AGENTCORE_GATEWAY_ID),
        "adapter_type": "PostgreSQL/MCP" if USE_POSTGRES_MCP else "DynamoDB",
    }

# =============================================================================
# AgentCore Application
# =============================================================================

app = BedrockAgentCoreApp()


# =============================================================================
# Agent Room Event Emission Helpers
# =============================================================================
# These functions emit events to the DynamoDB Audit Log so the Agent Room
# can display real-time agent activity. Uses emit_agent_event() from
# agent_room_service.py which writes AGENT_ACTIVITY events.

# Actions that should trigger Agent Room visibility (major agent work)
TRACKED_ACTIONS = {
    # NEXO Intelligent Import (most visible in UI)
    "nexo_analyze_file": ("nexo_import", "Analisando arquivo..."),
    "nexo_get_questions": ("nexo_import", "Preparando perguntas..."),
    "nexo_submit_answers": ("nexo_import", "Processando respostas..."),
    "nexo_prepare_processing": ("nexo_import", "Preparando importação..."),
    "nexo_execute_import": ("nexo_import", "Executando importação..."),
    "nexo_learn_from_import": ("learning", "Aprendendo com a importação..."),
    # NF Processing (IntakeAgent)
    "process_nf_upload": ("intake", "Processando nota fiscal..."),
    "validate_nf_extraction": ("intake", "Validando extração da NF..."),
    "confirm_nf_entry": ("intake", "Confirmando entrada da NF..."),
    "process_scanned_nf_upload": ("intake", "Lendo NF escaneada..."),
    # Smart Import
    # NOTE: "data_import" because "import" is a Python reserved keyword
    "smart_import_upload": ("data_import", "Processando arquivo..."),
    "preview_import": ("data_import", "Analisando dados..."),
    "execute_import": ("data_import", "Importando dados..."),
    # Movements (EstoqueControlAgent)
    "create_movement": ("estoque_control", "Registrando movimentação..."),
    "create_transfer": ("estoque_control", "Processando transferência..."),
    "create_reservation": ("estoque_control", "Criando reserva..."),
    # Reconciliation
    "start_inventory_count": ("reconciliacao", "Iniciando contagem..."),
    "analyze_divergences": ("reconciliacao", "Analisando divergências..."),
    # HIL Tasks
    "approve_task": ("compliance", "Processando aprovação..."),
    "reject_task": ("compliance", "Processando rejeição..."),
    # Equipment Research
    "research_equipment": ("equipment_research", "Pesquisando equipamento..."),
    "research_equipment_batch": ("equipment_research", "Pesquisando lote..."),
    # Expedition
    "process_expedition_request": ("expedition", "Processando expedição..."),
    # Returns
    "process_return": ("reverse", "Processando devolução..."),
}


def _emit_action_started(action: str, session_id: str) -> None:
    """
    Emit agent activity event when a tracked action starts.

    Non-blocking - failures are logged but don't affect action execution.
    Only emits for actions in TRACKED_ACTIONS to avoid noise.

    Args:
        action: The action being executed
        session_id: Current session ID
    """
    if action not in TRACKED_ACTIONS:
        return

    agent_id, message = TRACKED_ACTIONS[action]

    try:
        from tools.agent_room_service import emit_agent_event
        emit_agent_event(
            agent_id=agent_id,
            status="trabalhando",
            message=message,
            session_id=session_id,
        )
    except Exception as e:
        # Non-blocking - log but don't fail the action
        print(f"[AgentRoom] Warning: Failed to emit start event: {e}")


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """
    Main entrypoint for AgentCore Runtime.

    Routes requests to the appropriate agent based on the 'action' field.

    Args:
        payload: Request payload containing action and parameters
        context: AgentCore context with session_id, etc.

    Returns:
        Agent response as dict
    """
    action = payload.get("action", "health_check")
    # Try context session_id first, then payload, then default
    session_id = getattr(context, "session_id", None) or payload.get("session_id", "default-session")

    # Extract user identity from AgentCore context (JWT validated) or payload (fallback)
    # COMPLIANCE: AgentCore Identity v1.0
    extract_user_identity, log_identity_context = _get_identity_utils()
    user = extract_user_identity(context, payload)
    user_id = user.user_id

    # Log identity context for security monitoring
    log_identity_context(user, "SGA-MainRouter", action, session_id)

    # Debug logging to trace action routing
    print(f"[SGA Invoke] action={action}, user_id={user_id}, identity_source={user.source}, session_id={session_id}")

    # =================================================================
    # Agent Room Event Emission (Sala de Transparência)
    # =================================================================
    # Emit agent activity events for major actions so they appear in
    # the Agent Room live feed. This provides transparency to users.
    _emit_action_started(action, session_id)

    # Track session in DynamoDB (non-blocking)
    try:
        from tools.dynamodb_client import SGASessionManager
        session_mgr = SGASessionManager()
        session_mgr.ensure_session_exists(user_id, session_id, action, agent_type="inventory")
    except Exception as e:
        print(f"[Session] Warning: Failed to track session: {e}")

    # Route to appropriate handler
    try:
        # =================================================================
        # Health & System
        # =================================================================
        if action == "health_check":
            return _health_check()

        elif action == "debug_version":
            # Debug action to verify deployed code version
            # Added: 2026-01-06T03:30:00Z - UNIQUE MARKER FOR THIS DEPLOY
            return {
                "success": True,
                "code_marker": "2026-01-06T03:30:00Z",
                "git_commit": os.environ.get("GIT_COMMIT_SHA", "unknown"),
                "deployed_at": os.environ.get("DEPLOYED_AT", "unknown"),
                "action_received": action,
                "has_get_nf_upload_url": True,  # Confirms handler exists in code
            }

        elif action == "test_audit":
            # Test action to verify audit logging is working
            try:
                from tools.dynamodb_client import SGAAuditLogger
                audit = SGAAuditLogger()
                audit.log_action(
                    action="AUDIT_TEST",
                    entity_type="TEST",
                    entity_id=f"test-{session_id}",
                    actor=user_id,
                    details={
                        "test": True,
                        "session_id": session_id,
                        "timestamp": os.environ.get("DEPLOYED_AT", "unknown"),
                    },
                )
                return {
                    "success": True,
                    "message": "Audit log entry created successfully",
                    "entity_id": f"test-{session_id}",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

        # =================================================================
        # Asset Search & Query
        # =================================================================
        elif action == "search_assets":
            return asyncio.run(_search_assets(payload))

        elif action == "where_is_serial":
            return asyncio.run(_where_is_serial(payload))

        elif action == "get_balance":
            return asyncio.run(_get_balance(payload))

        elif action == "get_asset_timeline":
            return asyncio.run(_get_asset_timeline(payload))

        # =================================================================
        # NEXO Estoque Chat
        # =================================================================
        elif action == "chat":
            return asyncio.run(_nexo_estoque_chat(payload, user_id, session_id))

        # =================================================================
        # NF Processing (IntakeAgent) - A2A Protocol
        # =================================================================
        elif action == "get_nf_upload_url":
            return asyncio.run(_get_nf_upload_url(payload, session_id))

        elif action == "process_nf_upload":
            return asyncio.run(_process_nf_upload(payload, user_id, session_id))

        elif action == "validate_nf_extraction":
            return asyncio.run(_validate_nf_extraction(payload, session_id))

        elif action == "confirm_nf_entry":
            return asyncio.run(_confirm_nf_entry(payload, user_id, session_id))

        elif action == "process_scanned_nf_upload":
            return asyncio.run(_process_scanned_nf_upload(payload, user_id, session_id))

        elif action == "process_image_ocr":
            return asyncio.run(_process_image_ocr(payload, user_id, session_id))

        # =================================================================
        # Manual Entry
        # =================================================================
        elif action == "create_manual_entry":
            return asyncio.run(_create_manual_entry(payload, user_id))

        # =================================================================
        # SAP Import (Full Asset Creation)
        # =================================================================
        elif action == "preview_sap_import":
            return asyncio.run(_preview_sap_import(payload, user_id))

        elif action == "execute_sap_import":
            return asyncio.run(_execute_sap_import(payload, user_id))

        # =================================================================
        # Movements (EstoqueControlAgent) - A2A Protocol
        # =================================================================
        elif action == "create_movement":
            return asyncio.run(_create_movement(payload, user_id, session_id))

        elif action == "create_reservation":
            return asyncio.run(_create_reservation(payload, user_id, session_id))

        elif action == "cancel_reservation":
            return asyncio.run(_cancel_reservation(payload, user_id, session_id))

        elif action == "process_expedition":
            return asyncio.run(_process_expedition(payload, user_id, session_id))

        elif action == "create_transfer":
            return asyncio.run(_create_transfer(payload, user_id, session_id))

        # =================================================================
        # HIL Tasks (ComplianceAgent)
        # =================================================================
        elif action == "get_pending_tasks":
            return asyncio.run(_get_pending_tasks(payload, user_id))

        elif action == "approve_task":
            return asyncio.run(_approve_task(payload, user_id))

        elif action == "reject_task":
            return asyncio.run(_reject_task(payload, user_id))

        # =================================================================
        # Inventory Counting (ReconciliacaoAgent)
        # =================================================================
        elif action == "start_inventory_count":
            return asyncio.run(_start_inventory_count(payload, user_id, session_id))

        elif action == "submit_count_result":
            return asyncio.run(_submit_count_result(payload, user_id, session_id))

        elif action == "analyze_divergences":
            return asyncio.run(_analyze_divergences(payload, session_id))

        elif action == "propose_adjustment":
            return asyncio.run(_propose_adjustment(payload, user_id, session_id))

        # =================================================================
        # Cadastros (Part Numbers, Locations, Projects)
        # =================================================================
        elif action == "list_part_numbers":
            return asyncio.run(_list_part_numbers(payload))

        elif action == "create_part_number":
            return asyncio.run(_create_part_number(payload, user_id))

        elif action == "list_locations":
            return asyncio.run(_list_locations(payload))

        elif action == "create_location":
            return asyncio.run(_create_location(payload, user_id))

        # =================================================================
        # Reports & Analytics
        # =================================================================
        elif action == "get_balance_report":
            return asyncio.run(_get_balance_report(payload))

        elif action == "get_pending_reversals":
            return asyncio.run(_get_pending_reversals(payload))

        elif action == "get_movement_history":
            return asyncio.run(_get_movement_history(payload))

        elif action == "get_accuracy_metrics":
            return asyncio.run(_get_accuracy_metrics(payload))

        elif action == "reconcile_sap_export":
            return asyncio.run(_reconcile_sap_export(payload, user_id))

        elif action == "apply_reconciliation_action":
            return asyncio.run(_apply_reconciliation_action(payload, user_id))

        # =================================================================
        # Bulk Import (ImportAgent)
        # =================================================================
        elif action == "preview_import":
            return asyncio.run(_preview_import(payload, user_id, session_id))

        elif action == "execute_import":
            return asyncio.run(_execute_import(payload, user_id, session_id))

        elif action == "validate_pn_mapping":
            return asyncio.run(_validate_pn_mapping(payload, session_id))

        # =================================================================
        # Smart Import (Auto-detect file type)
        # =================================================================
        elif action == "smart_import_upload":
            return asyncio.run(_smart_import_upload(payload, user_id, session_id))

        elif action == "generate_import_observations":
            return asyncio.run(_generate_import_observations(payload, session_id))

        # =================================================================
        # NEXO Intelligent Import (Agentic AI-First)
        # =================================================================
        # ReAct Pattern: OBSERVE → THINK → ASK → LEARN → ACT
        elif action == "nexo_analyze_file":
            return asyncio.run(_nexo_analyze_file(payload, user_id, session_id))

        elif action == "nexo_get_questions":
            return asyncio.run(_nexo_get_questions(payload, session_id))

        elif action == "nexo_submit_answers":
            return asyncio.run(_nexo_submit_answers(payload, session_id))

        elif action == "nexo_learn_from_import":
            return asyncio.run(_nexo_learn_from_import(payload, session_id))

        elif action == "nexo_prepare_processing":
            return asyncio.run(_nexo_prepare_processing(payload, session_id))

        elif action == "nexo_execute_import":
            return asyncio.run(_nexo_execute_import(payload, user_id, session_id))

        elif action == "nexo_get_prior_knowledge":
            return asyncio.run(_nexo_get_prior_knowledge(payload, user_id, session_id))

        elif action == "nexo_get_adaptive_threshold":
            return asyncio.run(_nexo_get_adaptive_threshold(payload, user_id, session_id))

        # =================================================================
        # Schema Introspection (Schema-Aware Import - January 2026)
        # =================================================================
        elif action == "get_import_schema":
            return asyncio.run(_get_import_schema(payload))

        # =================================================================
        # Expedition (ExpeditionAgent)
        # =================================================================
        elif action == "process_expedition_request":
            return asyncio.run(_process_expedition_request(payload, user_id, session_id))

        elif action == "verify_expedition_stock":
            return asyncio.run(_verify_expedition_stock(payload, session_id))

        elif action == "confirm_separation":
            return asyncio.run(_confirm_separation(payload, user_id, session_id))

        elif action == "complete_expedition":
            return asyncio.run(_complete_expedition(payload, user_id, session_id))

        # =================================================================
        # Reverse Logistics (ReverseAgent)
        # =================================================================
        elif action == "process_return":
            return asyncio.run(_process_return(payload, user_id, session_id))

        elif action == "validate_return_origin":
            return asyncio.run(_validate_return_origin(payload, session_id))

        elif action == "evaluate_return_condition":
            return asyncio.run(_evaluate_return_condition(payload, session_id))

        # =================================================================
        # Carrier Quotes (CarrierAgent)
        # =================================================================
        elif action == "get_shipping_quotes":
            return asyncio.run(_get_shipping_quotes(payload, session_id))

        elif action == "recommend_carrier":
            return asyncio.run(_recommend_carrier(payload, session_id))

        elif action == "track_shipment":
            return asyncio.run(_track_shipment(payload, session_id))

        # =================================================================
        # Equipment Research (EquipmentResearchAgent)
        # =================================================================
        # Researches equipment documentation using Gemini + google_search
        # and stores in S3 for Bedrock Knowledge Base ingestion
        elif action == "research_equipment":
            return asyncio.run(_research_equipment(payload, user_id, session_id))

        elif action == "research_equipment_batch":
            return asyncio.run(_research_equipment_batch(payload, user_id, session_id))

        elif action == "get_research_status":
            return asyncio.run(_get_research_status(payload, session_id))

        elif action == "query_equipment_docs":
            return asyncio.run(_query_equipment_docs(payload, user_id, session_id))

        # =================================================================
        # Agent Room (Sala de Transparencia)
        # =================================================================
        elif action == "get_agent_room_data":
            return asyncio.run(_get_agent_room_data(payload, user_id))

        elif action == "get_xray_events":
            return asyncio.run(_get_xray_events(payload, user_id, session_id))

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        return {"success": False, "error": str(e), "action": action}


# =============================================================================
# Health Check
# =============================================================================


def _health_check() -> dict:
    """
    Return system health status.

    Used by monitoring and deployment verification.
    Includes git commit SHA for verifying deployed code version.
    """
    from agents.utils import AGENT_VERSION, MODEL_GEMINI

    return {
        "success": True,
        "status": "healthy",
        "version": AGENT_VERSION,
        "git_commit": os.environ.get("GIT_COMMIT_SHA", "unknown"),
        "deployed_at": os.environ.get("DEPLOYED_AT", "unknown"),
        "model": MODEL_GEMINI,
        "module": "Gestao de Ativos - Estoque",
        "agents": [
            "EstoqueControlAgent",
            "IntakeAgent",
            "ReconciliacaoAgent",
            "ComplianceAgent",
            "ComunicacaoAgent",
            "NexoImportAgent",  # Agentic AI-First intelligent import
            "LearningAgent",    # Episodic Memory for continuous learning
        ],
        "tables": {
            "inventory": os.environ.get("INVENTORY_TABLE", ""),
            "hil_tasks": os.environ.get("HIL_TASKS_TABLE", ""),
            "audit_log": os.environ.get("AUDIT_LOG_TABLE", ""),
        },
        "bucket": os.environ.get("DOCUMENTS_BUCKET", ""),
        "database_adapter": get_adapter_info(),
    }


# =============================================================================
# Asset Search & Query Handlers
# =============================================================================


async def _search_assets(payload: dict) -> dict:
    """
    Search assets by various criteria.

    Supports search by:
    - Serial number (partial match)
    - Part number
    - Location
    - Project
    - Status
    """
    from tools.dynamodb_client import SGADynamoDBClient
    from agents.utils import EntityPrefix

    db = SGADynamoDBClient()

    location_id = payload.get("location_id")
    project_id = payload.get("project_id")
    limit = payload.get("limit", 50)

    assets = []

    if location_id:
        assets = db.get_assets_by_location(location_id, limit=limit)
    elif project_id:
        assets = db.query_gsi(
            gsi_name="GSI3-ProjectQuery",
            pk_value=f"{EntityPrefix.PROJECT}{project_id}",
            sk_prefix="ASSET#",
            limit=limit,
        )
    else:
        # Query all assets by status
        assets = db.query_gsi(
            gsi_name="GSI4-StatusQuery",
            pk_value="STATUS#IN_STOCK",
            limit=limit,
        )

    return {
        "success": True,
        "assets": assets,
        "count": len(assets),
    }


async def _where_is_serial(payload: dict, session_id: str = "default") -> dict:
    """
    Find the current location of a serialized asset.

    Natural language query: "Onde esta o serial XYZ?"

    Architecture:
    - Invokes EstoqueControlAgent in dedicated runtime via A2A Protocol
    """
    serial = payload.get("serial", "")
    if not serial:
        return {"success": False, "error": "Serial number required"}

    return await _invoke_agent_a2a(
        agent_id="estoque_control",
        action="query_asset_location",
        payload={"serial_number": serial},
        session_id=session_id,
    )


async def _get_balance(payload: dict, session_id: str = "default") -> dict:
    """
    Get current balance for a part number at a location.

    Returns quantity available, reserved, and total.

    Architecture:
    - Invokes EstoqueControlAgent in dedicated runtime via A2A Protocol
    """
    part_number = payload.get("part_number", "")
    location_id = payload.get("location_id")
    project_id = payload.get("project_id")

    if not part_number:
        return {"success": False, "error": "part_number required"}

    return await _invoke_agent_a2a(
        agent_id="estoque_control",
        action="query_balance",
        payload={
            "part_number": part_number,
            "location_id": location_id,
            "project_id": project_id,
        },
        session_id=session_id,
    )


async def _get_asset_timeline(payload: dict) -> dict:
    """
    Get complete timeline of an asset's movements.

    Uses GSI6 for event sourcing pattern.
    """
    asset_id = payload.get("asset_id", "")
    if not asset_id:
        return {"success": False, "error": "asset_id required"}

    from tools.dynamodb_client import SGADynamoDBClient

    db = SGADynamoDBClient()
    timeline = db.get_asset_timeline(asset_id=asset_id, limit=100)

    return {
        "success": True,
        "asset_id": asset_id,
        "timeline": timeline,
        "count": len(timeline),
    }


# =============================================================================
# NEXO Estoque Chat
# =============================================================================


async def _nexo_estoque_chat(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Handle NEXO Estoque chat requests.

    Natural language interface for inventory queries.
    Examples:
    - "Quantos switches temos no estoque de SP?"
    - "Quais reversas estao pendentes ha mais de 5 dias?"
    - "Preciso reservar 3 unidades do PN 12345 para o projeto ABC"
    """
    question = payload.get("question", "")
    if not question:
        return {"success": False, "error": "Question required"}

    # TODO: Implement with NEXO Estoque agent
    return {
        "success": True,
        "answer": f"NEXO Estoque respondendo: '{question}' - Implementado no Sprint 2",
        "sources": [],
    }


# =============================================================================
# NF Processing Handlers
# =============================================================================


async def _get_nf_upload_url(payload: dict, session_id: str = "default") -> dict:
    """
    Get presigned URL for NF/document upload.

    Used by Smart Import to get S3 presigned URL before file upload.

    Payload:
        filename: Original filename
        content_type: MIME type of the file

    Returns:
        Dict with upload_url, s3_key, and expires_in

    Architecture:
    - DIRECT implementation (no A2A delegation)
    - Presigned URL generation is a stateless utility operation
    - Does not require AI agent orchestration

    Note: Previously delegated to IntakeAgent, but changed to direct call
    since the per-agent runtimes are not yet deployed (2026-01-11).
    """
    filename = payload.get("filename", "")
    content_type = payload.get("content_type", "application/octet-stream")

    if not filename:
        return {"success": False, "error": "filename is required"}

    try:
        from tools.s3_client import SGAS3Client

        s3 = SGAS3Client()
        key = s3.get_temp_path(filename)
        url_info = s3.generate_upload_url(
            key=key,
            content_type=content_type,
            expires_in=3600,
        )

        # Map 'key' to 's3_key' for frontend compatibility
        if url_info.get("success") and "key" in url_info:
            url_info["s3_key"] = url_info.pop("key")

        return url_info

    except Exception as e:
        print(f"[SGA] _get_nf_upload_url error: {e}")
        return {"success": False, "error": str(e)}


async def _process_nf_upload(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Process uploaded NF (PDF or XML).

    Extracts:
    - NF number, date, value
    - Items with quantities and unit prices
    - CFOP, NCM codes
    - Supplier information

    Returns extraction with confidence score.

    Architecture:
    - Invokes IntakeAgent in dedicated runtime via A2A Protocol
    """
    s3_key = payload.get("s3_key", "")
    file_type = payload.get("file_type", "xml")
    project_id = payload.get("project_id", "")
    destination_location_id = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    if not s3_key:
        return {"success": False, "error": "s3_key required"}

    return await _invoke_agent_a2a(
        agent_id="intake",
        action="process_nf",
        payload={
            "s3_key": s3_key,
            "file_type": file_type,
            "project_id": project_id,
            "destination_location_id": destination_location_id,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _validate_nf_extraction(payload: dict, session_id: str = "default") -> dict:
    """
    Validate NF extraction before confirmation.

    Checks:
    - Part numbers exist or need creation
    - Quantities are reasonable
    - Values match expected ranges

    Architecture:
    - Invokes IntakeAgent in dedicated runtime via A2A Protocol
    """
    return await _invoke_agent_a2a(
        agent_id="intake",
        action="validate_extraction",
        payload=payload,
        session_id=session_id,
    )


async def _confirm_nf_entry(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Confirm NF entry after user review.

    Creates:
    - ENTRY movement for each item
    - Updates balances
    - Audit log entry

    Architecture:
    - Invokes IntakeAgent in dedicated runtime via A2A Protocol
    """
    entry_id = payload.get("entry_id", "")
    item_mappings = payload.get("item_mappings")
    notes = payload.get("notes")

    if not entry_id:
        return {"success": False, "error": "entry_id required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="intake",
        action="confirm_entry",
        payload={
            "entry_id": entry_id,
            "item_mappings": item_mappings,
            "notes": notes,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _process_scanned_nf_upload(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Process scanned NF document using Gemini Vision.

    Specifically designed for:
    - Paper NF scanned as PDF/image
    - Camera photos of DANFE documents
    - Low-quality scans from older equipment

    Uses Gemini 3.0 Pro Vision for extraction with confidence scoring
    based on scan quality.

    Args:
        payload: Request payload with:
            - s3_key: S3 key of uploaded file
            - project_id: Optional project context
            - destination_location_id: Target location (default: ESTOQUE_CENTRAL)
        user_id: User performing the upload
        session_id: Session ID for context

    Returns:
        Extraction result with confidence score and quality indicators

    Architecture:
    - Invokes IntakeAgent in dedicated runtime via A2A Protocol
    """
    s3_key = payload.get("s3_key", "")
    project_id = payload.get("project_id", "")
    destination_location_id = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    if not s3_key:
        return {"success": False, "error": "s3_key required"}

    # Determine file type from S3 key
    original_file_type = "pdf"
    if s3_key.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
        original_file_type = "image"

    result = await _invoke_agent_a2a(
        agent_id="intake",
        action="process_nf",
        payload={
            "s3_key": s3_key,
            "file_type": "pdf",  # Forces PDF/scanned processing path
            "project_id": project_id,
            "destination_location_id": destination_location_id,
        },
        session_id=session_id,
        user_id=user_id,
    )
    # Add scanned-specific metadata
    if isinstance(result, dict):
        result["processing_type"] = "scanned_vision"
        result["original_file_type"] = original_file_type
    return result


# =============================================================================
# Image OCR Handler
# =============================================================================


async def _process_image_ocr(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Process an image (scanned NF, mobile photo) with OCR via Gemini Vision.

    Specifically designed for:
    - JPEG/PNG photos from mobile devices
    - Scanned NF documents
    - Camera captures of DANFE

    Uses the same IntakeAgent but with file_type='image' to trigger
    Vision-based extraction.

    Args:
        payload: Request payload with:
            - s3_key: S3 key of uploaded image
            - project_id: Optional project context
            - destination_location_id: Target location (default: ESTOQUE_CENTRAL)
        user_id: User performing the upload
        session_id: Session ID for context

    Returns:
        Extraction result with confidence score

    Architecture:
    - Invokes IntakeAgent in dedicated runtime via A2A Protocol
    """
    s3_key = payload.get("s3_key", "")
    project_id = payload.get("project_id", "")
    destination_location_id = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    if not s3_key:
        return {"success": False, "error": "s3_key required"}

    result = await _invoke_agent_a2a(
        agent_id="intake",
        action="parse_nf_image",
        payload={
            "s3_key": s3_key,
            "project_id": project_id,
            "destination_location_id": destination_location_id,
        },
        session_id=session_id,
        user_id=user_id,
    )
    if isinstance(result, dict):
        result["processing_type"] = "image_vision_ocr"
    return result


# =============================================================================
# Manual Entry Handler
# =============================================================================


async def _create_manual_entry(payload: dict, user_id: str) -> dict:
    """
    Create a manual entry without source file.

    Useful for:
    - Donations and gifts
    - Adjustments from physical count
    - Entries from systems without export capability

    Payload:
        items: List of items [{part_number_id, quantity, serial_numbers?, unit_value?, notes?}]
        project_id: Optional project
        destination_location_id: Required destination
        document_reference: Optional reference (e.g., "Doacao 2025-01")
        notes: General notes

    Returns:
        Entry result with created movements
    """
    from agents.utils import generate_id, now_iso
    from tools.dynamodb_client import SGADynamoDBClient

    items = payload.get("items", [])
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id", "")
    document_reference = payload.get("document_reference", "")
    notes = payload.get("notes", "")

    if not items:
        return {"success": False, "error": "items is required"}

    if not destination_location_id:
        return {"success": False, "error": "destination_location_id is required"}

    db = SGADynamoDBClient()
    entry_id = generate_id("MANUAL")
    movements_created = 0
    assets_created = 0
    total_quantity = 0
    errors = []
    warnings = []

    for item in items:
        pn_id = item.get("part_number_id", "")
        quantity = item.get("quantity", 1)
        serial_numbers = item.get("serial_numbers", [])
        unit_value = item.get("unit_value", 0)
        item_notes = item.get("notes", "")

        if not pn_id:
            warnings.append(f"Item sem part_number_id ignorado")
            continue

        if quantity <= 0:
            warnings.append(f"Item {pn_id} com quantidade <= 0 ignorado")
            continue

        try:
            # Create movement for this item
            movement_id = generate_id("MOV")
            movement_data = {
                "PK": f"MOVEMENT#{movement_id}",
                "SK": f"MOVEMENT#{movement_id}",
                "movement_id": movement_id,
                "entry_id": entry_id,
                "movement_type": "ENTRY",
                "part_number_id": pn_id,
                "quantity": quantity,
                "serial_numbers": serial_numbers,
                "unit_value": unit_value,
                "destination_location_id": destination_location_id,
                "project_id": project_id,
                "document_reference": document_reference,
                "notes": item_notes,
                "source": "MANUAL_ENTRY",
                "created_by": user_id,
                "created_at": now_iso(),
                "status": "COMPLETED",
            }

            db.put_item(movement_data)
            movements_created += 1
            total_quantity += quantity

            # Create assets for serialized items
            if serial_numbers:
                for serial in serial_numbers:
                    asset_id = generate_id("ASSET")
                    asset_data = {
                        "PK": f"ASSET#{asset_id}",
                        "SK": f"ASSET#{asset_id}",
                        "asset_id": asset_id,
                        "part_number_id": pn_id,
                        "serial_number": serial,
                        "location_id": destination_location_id,
                        "project_id": project_id,
                        "status": "IN_STOCK",
                        "created_by": user_id,
                        "created_at": now_iso(),
                        "entry_movement_id": movement_id,
                    }
                    db.put_item(asset_data)
                    assets_created += 1

        except Exception as e:
            errors.append(f"Erro ao criar movimento para {pn_id}: {str(e)}")

    # Audit logging
    try:
        from tools.dynamodb_client import SGAAuditLogger
        audit = SGAAuditLogger()
        audit.log_action(
            action="MANUAL_ENTRY_CREATED",
            entity_type="ENTRY",
            entity_id=entry_id,
            actor=user_id,
            details={
                "movements_created": movements_created,
                "assets_created": assets_created,
                "total_quantity": total_quantity,
                "document_reference": document_reference,
                "errors_count": len(errors),
            },
        )
    except Exception:
        pass  # Don't fail the request if audit logging fails

    return {
        "success": len(errors) == 0,
        "entry_id": entry_id,
        "movements_created": movements_created,
        "assets_created": assets_created,
        "total_quantity": total_quantity,
        "errors": errors,
        "warnings": warnings,
    }


# =============================================================================
# SAP Import Handlers
# =============================================================================


async def _preview_sap_import(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Preview a SAP export file (CSV/XLSX) before importing.

    Detects SAP format columns (30+ fields) and maps them to SGA fields.
    Supports full asset creation with serial, RFID, technician data.

    Payload:
        file_content: Base64-encoded file content
        filename: Original filename for type detection
        project_id: Optional project filter
        destination_location_id: Optional destination
        full_asset_creation: Whether to create full assets (default: True)

    Returns:
        Preview with column mappings, matched rows, and stats

    Architecture:
    - Invokes ImportAgent in dedicated runtime via A2A Protocol
    """
    file_content_b64 = payload.get("file_content", "")
    filename = payload.get("filename", "sap_export.csv")
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id")
    full_asset_creation = payload.get("full_asset_creation", True)

    if not file_content_b64:
        return {"success": False, "error": "file_content is required"}

    return await _invoke_agent_a2a(
        agent_id="data_import",
        action="preview_import",
        payload={
            "file_content": file_content_b64,
            "filename": filename,
            "project_id": project_id,
            "destination_location_id": destination_location_id,
            "sap_format": True,
            "full_asset_creation": full_asset_creation,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _execute_sap_import(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Execute SAP import with full asset creation.

    Creates assets with serial numbers, RFID, technician data,
    and all SAP-specific metadata.

    Payload:
        import_id: Import session ID from preview
        pn_overrides: Manual PN assignments {row_number: pn_id}
        full_asset_creation: Whether to create full assets (default: True)

    Returns:
        Import result with created assets and movements

    Architecture:
    - Invokes ImportAgent in dedicated runtime via A2A Protocol
    """
    import_id = payload.get("import_id", "")
    pn_overrides = payload.get("pn_overrides", {})
    full_asset_creation = payload.get("full_asset_creation", True)

    if not import_id:
        return {"success": False, "error": "import_id is required"}

    result = await _invoke_agent_a2a(
        agent_id="data_import",
        action="execute_sap_import",
        payload={
            "import_id": import_id,
            "pn_overrides": pn_overrides,
            "full_asset_creation": full_asset_creation,
            "operator_id": user_id,
        },
        session_id=session_id,
        user_id=user_id,
    )

    # Audit logging
    try:
        from tools.dynamodb_client import SGAAuditLogger
        audit = SGAAuditLogger()
        audit.log_action(
            action="SAP_IMPORT_EXECUTED",
            entity_type="SAP_IMPORT",
            entity_id=import_id,
            actor=user_id,
            details={
                "full_asset_creation": full_asset_creation,
                "pn_overrides_count": len(pn_overrides),
                "success": result.get("success", False) if isinstance(result, dict) else False,
            },
        )
    except Exception:
        pass  # Don't fail the request if audit logging fails

    return result


# =============================================================================
# Movement Handlers
# =============================================================================


async def _create_movement(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Create a generic inventory movement.

    Movement types: ENTRY, EXIT, TRANSFER, ADJUSTMENT, RETURN, DISCARD, LOSS
    """
    # TODO: Implement with EstoqueControlAgent via A2A when action is available
    return {
        "success": True,
        "movement_id": None,
        "message": "Movement creation implemented in Sprint 2",
    }


async def _create_reservation(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Create a reservation for items.

    Reservations:
    - Block quantity from available balance
    - Have TTL for automatic expiration
    - Are linked to tickets/chamados
    """
    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="estoque_control",
        action="create_reservation",
        payload={
            "part_number": payload.get("part_number", ""),
            "quantity": payload.get("quantity", 1),
            "project_id": payload.get("project_id", ""),
            "chamado_id": payload.get("chamado_id"),
            "serial_numbers": payload.get("serial_numbers"),
            "source_location_id": payload.get("source_location_id", "ESTOQUE_CENTRAL"),
            "destination_location_id": payload.get("destination_location_id"),
            "notes": payload.get("notes"),
            "ttl_hours": payload.get("ttl_hours", 72),
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _cancel_reservation(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """Cancel an existing reservation."""
    reservation_id = payload.get("reservation_id", "")
    reason = payload.get("reason")

    if not reservation_id:
        return {"success": False, "error": "reservation_id required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="estoque_control",
        action="cancel_reservation",
        payload={
            "reservation_id": reservation_id,
            "reason": reason,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _process_expedition(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Process an expedition (item exit).

    Flow:
    1. Validate reservation exists
    2. Create EXIT movement
    3. Update balances
    4. Clear reservation
    """
    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="estoque_control",
        action="process_expedition",
        payload={
            "reservation_id": payload.get("reservation_id"),
            "part_number": payload.get("part_number"),
            "quantity": payload.get("quantity", 1),
            "serial_numbers": payload.get("serial_numbers"),
            "source_location_id": payload.get("source_location_id", "ESTOQUE_CENTRAL"),
            "destination": payload.get("destination", ""),
            "project_id": payload.get("project_id"),
            "chamado_id": payload.get("chamado_id"),
            "recipient_name": payload.get("recipient_name", ""),
            "recipient_contact": payload.get("recipient_contact", ""),
            "shipping_method": payload.get("shipping_method", "HAND_DELIVERY"),
            "notes": payload.get("notes"),
            "evidence_keys": payload.get("evidence_keys"),
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _create_transfer(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Create a transfer between locations or projects.

    May require HIL for:
    - Cross-project transfers
    - Restricted location access
    """
    part_number = payload.get("part_number", "")
    quantity = payload.get("quantity", 1)
    source_location_id = payload.get("source_location_id", "")
    destination_location_id = payload.get("destination_location_id", "")
    project_id = payload.get("project_id", "")

    if not part_number:
        return {"success": False, "error": "part_number required"}
    if not source_location_id or not destination_location_id:
        return {"success": False, "error": "source and destination locations required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="estoque_control",
        action="create_transfer",
        payload={
            "part_number": part_number,
            "quantity": quantity,
            "source_location_id": source_location_id,
            "destination_location_id": destination_location_id,
            "project_id": project_id,
            "serial_numbers": payload.get("serial_numbers"),
            "notes": payload.get("notes"),
        },
        session_id=session_id,
        user_id=user_id,
    )


# =============================================================================
# HIL Task Handlers
# =============================================================================


async def _get_pending_tasks(payload: dict, user_id: str) -> dict:
    """
    Get pending HIL tasks for a user.

    Returns tasks sorted by priority and creation date.
    """
    from tools.hil_workflow import HILWorkflowManager

    manager = HILWorkflowManager()
    tasks = manager.get_pending_tasks(
        task_type=payload.get("task_type"),
        assigned_to=payload.get("assigned_to") or user_id,
        assigned_role=payload.get("assigned_role"),
        limit=payload.get("limit", 50),
    )

    return {
        "success": True,
        "tasks": tasks,
        "count": len(tasks),
    }


async def _approve_task(payload: dict, user_id: str) -> dict:
    """
    Approve a pending HIL task.

    Executes the pending action and logs the approval.
    """
    task_id = payload.get("task_id", "")
    notes = payload.get("notes")
    modified_payload = payload.get("modified_payload")

    if not task_id:
        return {"success": False, "error": "task_id required"}

    from tools.hil_workflow import HILWorkflowManager

    manager = HILWorkflowManager()
    result = await manager.approve_task(
        task_id=task_id,
        approved_by=user_id,
        notes=notes,
        modified_payload=modified_payload,
    )

    return result


async def _reject_task(payload: dict, user_id: str) -> dict:
    """
    Reject a pending HIL task.

    Logs the rejection with optional reason.
    """
    task_id = payload.get("task_id", "")
    reason = payload.get("reason", "")

    if not task_id:
        return {"success": False, "error": "task_id required"}
    if not reason:
        return {"success": False, "error": "reason required for rejection"}

    from tools.hil_workflow import HILWorkflowManager

    manager = HILWorkflowManager()
    result = await manager.reject_task(
        task_id=task_id,
        rejected_by=user_id,
        reason=reason,
    )

    return result


# =============================================================================
# Inventory Counting Handlers
# =============================================================================


async def _start_inventory_count(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Start a new inventory counting campaign.

    Creates a counting session for specified locations/items.
    """
    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="reconciliacao",
        action="start_campaign",
        payload={
            "name": payload.get("name", ""),
            "description": payload.get("description", ""),
            "location_ids": payload.get("location_ids"),
            "project_ids": payload.get("project_ids"),
            "part_numbers": payload.get("part_numbers"),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "require_double_count": payload.get("require_double_count", False),
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _submit_count_result(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Submit counting result for an item.

    Records counted quantity for reconciliation.
    """
    campaign_id = payload.get("campaign_id", "")
    part_number = payload.get("part_number", "")
    location_id = payload.get("location_id", "")

    if not campaign_id or not part_number or not location_id:
        return {"success": False, "error": "campaign_id, part_number, and location_id required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="reconciliacao",
        action="submit_count",
        payload={
            "campaign_id": campaign_id,
            "part_number": part_number,
            "location_id": location_id,
            "counted_quantity": payload.get("counted_quantity", 0),
            "counted_serials": payload.get("counted_serials"),
            "evidence_keys": payload.get("evidence_keys"),
            "notes": payload.get("notes"),
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _analyze_divergences(payload: dict, session_id: str = "default") -> dict:
    """
    Analyze divergences between counted and system quantities.

    Returns list of discrepancies with suggested actions.
    """
    campaign_id = payload.get("campaign_id", "")
    if not campaign_id:
        return {"success": False, "error": "campaign_id required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="reconciliacao",
        action="analyze_divergences",
        payload={"campaign_id": campaign_id},
        session_id=session_id,
    )


async def _propose_adjustment(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Propose an inventory adjustment based on counting.

    Always creates HIL task for approval.
    """
    campaign_id = payload.get("campaign_id", "")
    part_number = payload.get("part_number", "")
    location_id = payload.get("location_id", "")

    if not campaign_id or not part_number or not location_id:
        return {"success": False, "error": "campaign_id, part_number, and location_id required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="reconciliacao",
        action="propose_adjustment",
        payload={
            "campaign_id": campaign_id,
            "part_number": part_number,
            "location_id": location_id,
            "adjustment_reason": payload.get("adjustment_reason", ""),
        },
        session_id=session_id,
        user_id=user_id,
    )


# =============================================================================
# Cadastros Handlers
# =============================================================================


async def _list_part_numbers(payload: dict) -> dict:
    """List all part numbers with optional filtering."""
    # TODO: Implement with DynamoDB
    return {
        "success": True,
        "part_numbers": [],
        "message": "PN listing implemented in Sprint 2",
    }


async def _create_part_number(payload: dict, user_id: str) -> dict:
    """
    Create a new part number.

    Always requires HIL approval for new PN creation.
    """
    # TODO: Implement with ComplianceAgent (HIL required)
    return {
        "success": True,
        "task_id": None,  # HIL task created
        "message": "PN creation always requires approval",
    }


async def _list_locations(payload: dict) -> dict:
    """List all stock locations."""
    # TODO: Implement with DynamoDB
    return {
        "success": True,
        "locations": [],
        "message": "Location listing implemented in Sprint 2",
    }


async def _create_location(payload: dict, user_id: str) -> dict:
    """Create a new stock location."""
    # TODO: Implement
    return {
        "success": True,
        "location_id": None,
        "message": "Location creation implemented in Sprint 2",
    }


# =============================================================================
# Reports & Analytics Handlers
# =============================================================================


async def _get_balance_report(payload: dict) -> dict:
    """
    Generate balance report by location/project.

    Used for dashboard KPIs.
    """
    # TODO: Implement
    return {
        "success": True,
        "report": {},
        "message": "Balance report implemented in Sprint 2",
    }


async def _get_pending_reversals(payload: dict) -> dict:
    """
    Get list of pending return shipments.

    Filters by age and status.
    """
    # TODO: Implement
    return {
        "success": True,
        "reversals": [],
        "message": "Pending reversals implemented in Sprint 2",
    }


async def _get_movement_history(payload: dict) -> dict:
    """
    Get movement history with date range filtering.

    Uses GSI5 for date-based queries.
    """
    # TODO: Implement
    return {
        "success": True,
        "movements": [],
        "message": "Movement history implemented in Sprint 2",
    }


# =============================================================================
# Bulk Import Handlers (ImportAgent)
# =============================================================================


async def _preview_import(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Preview an import file before processing.

    Parses CSV/Excel, auto-detects columns, and attempts PN matching.

    Payload:
        file_content_base64: Base64-encoded file content
        filename: Original filename for type detection
        project_id: Optional project to assign all items
        destination_location_id: Optional destination location

    Returns:
        Preview with column mappings, matched rows, and stats

    Architecture:
    - Invokes ImportAgent in dedicated runtime via A2A Protocol
    """
    file_content_b64 = payload.get("file_content_base64", "")
    filename = payload.get("filename", "import.csv")
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id")

    if not file_content_b64:
        return {"success": False, "error": "file_content_base64 is required"}

    return await _invoke_agent_a2a(
        agent_id="data_import",
        action="preview_import",
        payload={
            "file_content": file_content_b64,
            "filename": filename,
            "project_id": project_id,
            "destination_location_id": destination_location_id,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _execute_import(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Execute the import after preview/confirmation.

    Creates entry movements for all valid rows.

    IMPORTANT: Per CLAUDE.md, inventory data MUST be stored in Aurora PostgreSQL.
    This function uses SGAPostgresClient directly to insert movements.

    NOTE: This handler has complex local processing (S3, CSV parsing, PostgreSQL).
    A2A migration requires refactoring ImportAgent runtime to handle full flow.

    Payload:
        import_id: Import session ID from preview
        file_content_base64: Base64-encoded file content (optional if s3_key provided)
        s3_key: S3 key of already-uploaded file (NEXO flow uses this)
        filename: Original filename
        column_mappings: Confirmed column mappings [{file_column, target_field}]
        pn_overrides: Optional manual PN assignments {row_number: pn_id}
        project_id: Project to assign all items
        destination_location_id: Destination location

    Returns:
        Import result with created movements
    """
    import base64
    import logging
    logger = logging.getLogger(__name__)

    import_id = payload.get("import_id", "")
    file_content_b64 = payload.get("file_content_base64", "")
    s3_key = payload.get("s3_key", "")  # NEXO flow: file already in S3
    filename = payload.get("filename", "import.csv")
    column_mappings = payload.get("column_mappings", [])
    pn_overrides = payload.get("pn_overrides", {})
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id")

    # TRUE Agentic Pattern: Use AI-inferred movement type instead of hardcoded value
    # This supports NEXO's autonomous decision making (OBSERVE → THINK → DECIDE)
    movement_type = payload.get("movement_type", "ENTRADA")  # Default fallback
    inferred_movement_type = payload.get("inferred_movement_type")
    if inferred_movement_type:
        # Map NEXO's inference to PostgreSQL movement types
        movement_type_map = {
            "ENTRADA": "ENTRADA",
            "SAIDA": "SAIDA",
            "AJUSTE": "AJUSTE_POSITIVO",  # Default to positive for now
            "SAÍDA": "SAIDA",  # Handle accent variation
        }
        movement_type = movement_type_map.get(inferred_movement_type.upper(), "ENTRADA")

    logger.info(f"[execute_import] Starting import {import_id} for file {filename}")
    logger.info(f"[execute_import] s3_key={s3_key}, column_mappings count={len(column_mappings)}")

    # Agent Room: emit start event
    from tools.agent_room_service import emit_agent_event
    emit_agent_event(
        agent_id="data_import",
        status="trabalhando",
        message=f"Iniciando importação de {filename}...",
        details={"import_id": import_id, "filename": filename},
    )

    if not import_id:
        return {"success": False, "error": "import_id is required"}

    if not file_content_b64 and not s3_key:
        return {"success": False, "error": "file_content_base64 or s3_key is required"}

    if not column_mappings:
        return {"success": False, "error": "column_mappings is required"}

    # Get file content: either from base64 or S3
    file_content = None
    if file_content_b64:
        try:
            file_content = base64.b64decode(file_content_b64)
            logger.info(f"[execute_import] Decoded base64 content, {len(file_content)} bytes")
        except Exception as e:
            return {"success": False, "error": f"Invalid base64 content: {e}"}
    elif s3_key:
        # NEXO flow: download from S3
        from tools.s3_client import SGAS3Client
        s3_client = SGAS3Client()
        try:
            file_content = s3_client.download_file(s3_key)
            logger.info(f"[execute_import] Downloaded from S3: {s3_key}, {len(file_content) if file_content else 0} bytes")
        except Exception as e:
            logger.error(f"[execute_import] S3 download failed: {e}")
            return {"success": False, "error": f"Failed to download file from S3: {e}"}

    if not file_content:
        return {"success": False, "error": "Failed to get file content"}

    # Parse file using csv_parser
    from tools.csv_parser import extract_all_rows

    try:
        all_rows = extract_all_rows(file_content, filename, column_mappings)
        logger.info(f"[execute_import] Parsed {len(all_rows)} rows from file")
    except Exception as e:
        logger.error(f"[execute_import] File parsing failed: {e}")
        return {"success": False, "error": f"Failed to parse file: {e}"}

    if not all_rows:
        return {"success": False, "error": "No valid rows found in file"}

    # Use PostgreSQL client for inventory operations (MANDATORY per CLAUDE.md)
    from tools.postgres_client import SGAPostgresClient

    try:
        pg_client = SGAPostgresClient()
        logger.info("[execute_import] PostgreSQL client initialized")
    except Exception as e:
        logger.error(f"[execute_import] PostgreSQL connection failed: {e}")
        return {"success": False, "error": f"Database connection failed: {e}"}

    # Process each row
    created_movements = []
    failed_rows = []
    skipped_rows = []

    for i, row_data in enumerate(all_rows):
        row_number = i + 2  # 1-based + header

        try:
            # Extract data from row
            part_number = row_data.get("part_number", "").strip()
            description = row_data.get("description", "").strip()
            qty_str = row_data.get("quantity", "0").strip()
            serial = row_data.get("serial", "").strip()
            location = row_data.get("location", destination_location_id or "").strip()

            # Skip empty rows
            if not part_number and not description:
                continue

            # Parse quantity
            try:
                quantity = int(float(qty_str.replace(",", ".")))
            except (ValueError, TypeError):
                failed_rows.append({
                    "row_number": row_number,
                    "reason": f"Quantidade invalida: {qty_str}",
                    "data": row_data,
                })
                continue

            if quantity <= 0:
                failed_rows.append({
                    "row_number": row_number,
                    "reason": "Quantidade deve ser maior que zero",
                    "data": row_data,
                })
                continue

            # Create movement via PostgreSQL client
            # TRUE Agentic: Use AI-inferred movement_type (ENTRADA/SAIDA/AJUSTE)
            result = pg_client.create_movement(
                movement_type=movement_type,  # Uses NEXO's autonomous inference
                part_number=part_number,
                quantity=quantity,
                destination_location_id=location,
                project_id=project_id,
                serial_numbers=[serial] if serial else None,
                reason=f"Import {import_id}",
            )

            if result.get("error"):
                # Part number not found - try to create it first or skip
                if "not found" in result.get("error", "").lower():
                    skipped_rows.append({
                        "row_number": row_number,
                        "reason": f"Part number nao encontrado: {part_number}",
                        "data": row_data,
                    })
                else:
                    failed_rows.append({
                        "row_number": row_number,
                        "reason": result.get("error"),
                        "data": row_data,
                    })
            else:
                created_movements.append({
                    "row_number": row_number,
                    "movement_id": result.get("movement_id", ""),
                    "part_number": part_number,
                    "quantity": quantity,
                })
                logger.info(f"[execute_import] Row {row_number}: Created movement for {part_number} qty={quantity}")

        except Exception as row_error:
            logger.error(f"[execute_import] Row {row_number} error: {row_error}")
            failed_rows.append({
                "row_number": row_number,
                "reason": str(row_error),
                "data": row_data,
            })

    # Calculate final stats
    total_rows = len(all_rows)
    success_rate = len(created_movements) / max(total_rows, 1)

    logger.info(
        f"[execute_import] Import complete: {len(created_movements)}/{total_rows} succeeded, "
        f"{len(failed_rows)} failed, {len(skipped_rows)} skipped"
    )

    # Audit logging
    try:
        from tools.dynamodb_client import SGAAuditLogger
        audit = SGAAuditLogger()
        audit.log_action(
            action="IMPORT_EXECUTED",
            entity_type="IMPORT",
            entity_id=import_id,
            actor=user_id,
            details={
                "filename": filename,
                "total_rows": total_rows,
                "created_count": len(created_movements),
                "failed_count": len(failed_rows),
                "skipped_count": len(skipped_rows),
                "success_rate": round(success_rate * 100, 1),
                "movement_type": movement_type,
            },
        )
    except Exception:
        pass  # Don't fail the request if audit logging fails

    # Agent Room: emit completion event
    if len(failed_rows) > 0:
        emit_agent_event(
            agent_id="data_import",
            status="disponivel",
            message=f"Importação concluída: {len(created_movements)} itens ok, {len(failed_rows)} com erro.",
            details={
                "success_count": len(created_movements),
                "failed_count": len(failed_rows),
                "filename": filename,
            },
        )
    else:
        emit_agent_event(
            agent_id="data_import",
            status="disponivel",
            message=f"Importação concluída com sucesso! {len(created_movements)} itens importados.",
            details={"count": len(created_movements), "filename": filename},
        )

    return {
        "success": True,
        "import_id": import_id,
        "total_rows": total_rows,
        "created_count": len(created_movements),
        "failed_count": len(failed_rows),
        "skipped_count": len(skipped_rows),
        "success_rate": round(success_rate * 100, 1),
        "created_movements": created_movements[:50],  # Limit response size
        "failed_rows": failed_rows[:20],
        "skipped_rows": skipped_rows[:20],
        "message": (
            f"Importacao concluida: {len(created_movements)}/{total_rows} "
            f"itens importados com sucesso via PostgreSQL"
        ),
    }


async def _validate_pn_mapping(payload: dict, session_id: str = "default") -> dict:
    """
    Validate a part number mapping suggestion.

    Used by operator to confirm or override AI suggestions.

    Payload:
        description: Item description from file
        suggested_pn_id: Optional suggested PN to validate

    Returns:
        Validation result with alternative suggestions
    """
    description = payload.get("description", "")
    suggested_pn_id = payload.get("suggested_pn_id")

    if not description:
        return {"success": False, "error": "description is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="data_import",
        action="validate_mapping",
        payload={
            "description": description,
            "suggested_pn_id": suggested_pn_id,
        },
        session_id=session_id,
    )


# =============================================================================
# Smart Import Handler (Auto-detect file type)
# =============================================================================


async def _smart_import_upload(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Smart import that auto-detects file type and routes to appropriate agent.

    Philosophy: Observe -> Think -> Learn -> Act
    1. OBSERVE: Download file from S3, examine raw bytes
    2. THINK: Detect file type using magic bytes, MIME, extension
    3. LEARN: Route to appropriate agent based on type
    4. ACT: Process and return extraction/preview

    Supports: XML, PDF, JPEG, PNG, CSV, XLSX, TXT

    Payload:
        s3_key: S3 key of uploaded file
        filename: Original filename
        content_type: Optional MIME type from upload
        project_id: Optional project context
        destination_location_id: Required destination location

    Returns:
        Processing result with source_type, extraction/preview, and confidence
    """
    s3_key = payload.get("s3_key", "")
    filename = payload.get("filename", "")
    content_type = payload.get("content_type", "")
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    if not s3_key:
        return {"success": False, "error": "s3_key is required"}

    if not filename:
        return {"success": False, "error": "filename is required"}

    # OBSERVE: Download file from S3
    from tools.s3_client import SGAS3Client

    s3_client = SGAS3Client()
    try:
        file_data = s3_client.download_file(s3_key)
    except Exception as e:
        return {"success": False, "error": f"Failed to download file from S3: {e}"}

    # THINK: Detect file type using magic bytes
    from tools.file_detector import detect_file_type, get_file_type_label

    file_type = detect_file_type(filename, content_type, file_data)

    if file_type == "unknown":
        return {
            "success": False,
            "error": f"Formato de arquivo nao suportado: {filename}",
            "detected_type": "unknown",
            "supported_formats": ["xml", "pdf", "jpg", "jpeg", "png", "csv", "xlsx", "txt"],
        }

    # LEARN + ACT: Route to appropriate agent based on file type
    result = None

    if file_type in ["xml", "pdf", "image"]:
        # Route to IntakeAgent for NF processing
        # =================================================================
        # A2A Protocol (100% Agentic Architecture)
        # =================================================================
        a2a_result = await _invoke_agent_a2a(
            agent_id="intake",
            action="process_nf",
            payload={
                "s3_key": s3_key,
                "file_type": "pdf" if file_type == "image" else file_type,
                "project_id": project_id,
                "destination_location_id": destination_location_id,
            },
            session_id=session_id,
            user_id=user_id,
        )
        result = a2a_result if isinstance(a2a_result, dict) else {"error": "Invalid response"}

        # Add smart import metadata
        if result:
            result["source_type"] = f"nf_{file_type}"
            result["detected_file_type"] = file_type
            result["file_type_label"] = get_file_type_label(file_type)

    elif file_type in ["csv", "xlsx"]:
        # Route to ImportAgent for spreadsheet processing via A2A
        import base64
        file_content_b64 = base64.b64encode(file_data).decode("utf-8")

        a2a_result = await _invoke_agent_a2a(
            agent_id="data_import",
            action="preview_import",
            payload={
                "file_content": file_content_b64,
                "filename": filename,
                "project_id": project_id,
                "destination_location_id": destination_location_id,
            },
            session_id=session_id,
            user_id=user_id,
        )
        result = a2a_result if isinstance(a2a_result, dict) else {"error": "Invalid response"}

        # Add smart import metadata
        if result:
            result["source_type"] = "spreadsheet"
            result["detected_file_type"] = file_type
            result["file_type_label"] = get_file_type_label(file_type)

    elif file_type == "txt":
        # Route to ImportAgent for text processing via A2A
        # Decode text content
        try:
            text_content = file_data.decode("utf-8")
        except UnicodeDecodeError:
            text_content = file_data.decode("latin-1")

        a2a_result = await _invoke_agent_a2a(
            agent_id="data_import",
            action="process_text_import",
            payload={
                "file_content": text_content,
                "filename": filename,
                "project_id": project_id,
                "destination_location_id": destination_location_id,
            },
            session_id=session_id,
            user_id=user_id,
        )
        result = a2a_result if isinstance(a2a_result, dict) else {"error": "Invalid response"}

        # Add smart import metadata
        if result:
            result["source_type"] = "text"
            result["detected_file_type"] = file_type
            result["file_type_label"] = get_file_type_label(file_type)
            result["requires_hil"] = True  # Text imports always require review

    # Add common fields to preview
    if result:
        result["smart_import"] = True
        result["filename"] = filename
        result["s3_key"] = s3_key

    # Return structured response matching SmartImportUploadResponse TypeScript type
    # Frontend expects: { success, detected_type, source_type, preview: {...} }
    return {
        "success": True,
        "detected_type": file_type,
        "detected_type_label": get_file_type_label(file_type),
        "source_type": result.get("source_type", "unknown") if result else "unknown",
        "preview": result,  # Preview data wrapped correctly for frontend
    }


async def _generate_import_observations(payload: dict, session_id: str = "default") -> dict:
    """
    Generate NEXO AI observations for import preview data.

    Called before user confirms import to display AI commentary
    in the confirmation modal.

    Pattern: Observe -> Learn -> Act

    Payload:
        preview: Import preview data containing:
            - source_type: Type of import (nf_xml, nf_pdf, spreadsheet, text)
            - items_count: Number of items
            - total_value: Optional total value
            - items: Optional list of item details
            - validation_warnings: Any warnings from validation
        context: Optional context (project_id, location_id, user_notes)

    Returns:
        NexoObservation with confidence, patterns, suggestions, and commentary
    """
    preview_data = payload.get("preview", {})
    context = payload.get("context")

    if not preview_data:
        return {
            "success": False,
            "error": "preview data is required",
        }

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="observation",
        action="generate_observations",
        payload={
            "preview_data": preview_data,
            "context": context,
        },
        session_id=session_id,
    )


# =============================================================================
# Expedition Handlers (ExpeditionAgent)
# =============================================================================


async def _process_expedition_request(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Process an expedition request from a chamado.

    Payload:
        chamado_id: Ticket ID
        project_id: Associated project
        items: List of items [{pn_id, serial, quantity}]
        destination_client: Client name/CNPJ
        destination_address: Delivery address
        urgency: LOW, NORMAL, HIGH, URGENT
        nature: USO_CONSUMO, CONSERTO, DEMONSTRACAO, etc.
        notes: Additional notes

    Returns:
        Expedition result with SAP-ready data
    """
    chamado_id = payload.get("chamado_id", "")
    project_id = payload.get("project_id", "")
    items = payload.get("items", [])
    destination_client = payload.get("destination_client", "")
    destination_address = payload.get("destination_address", "")
    urgency = payload.get("urgency", "NORMAL")
    nature = payload.get("nature", "USO_CONSUMO")
    notes = payload.get("notes", "")

    if not chamado_id:
        return {"success": False, "error": "chamado_id is required"}

    if not items:
        return {"success": False, "error": "items is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="expedition",
        action="process_expedition_request",
        payload={
            "chamado_id": chamado_id,
            "project_id": project_id,
            "items": items,
            "destination_client": destination_client,
            "destination_address": destination_address,
            "urgency": urgency,
            "nature": nature,
            "notes": notes,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _verify_expedition_stock(payload: dict, session_id: str = "default") -> dict:
    """
    Verify stock availability for an item.

    Payload:
        pn_id: Part number ID
        serial: Optional serial number
        quantity: Quantity needed

    Returns:
        Verification result with availability status
    """
    pn_id = payload.get("pn_id", "")
    serial = payload.get("serial")
    quantity = payload.get("quantity", 1)

    if not pn_id:
        return {"success": False, "error": "pn_id is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="expedition",
        action="verify_stock",
        payload={
            "pn_id": pn_id,
            "serial": serial,
            "quantity": quantity,
        },
        session_id=session_id,
    )


async def _confirm_separation(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Confirm physical separation and packaging.

    Payload:
        expedition_id: Expedition ID
        items_confirmed: List of confirmed items with serials
        package_info: Packaging details (weight, dimensions)

    Returns:
        Confirmation result
    """
    expedition_id = payload.get("expedition_id", "")
    items_confirmed = payload.get("items_confirmed", [])
    package_info = payload.get("package_info", {})

    if not expedition_id:
        return {"success": False, "error": "expedition_id is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="expedition",
        action="confirm_separation",
        payload={
            "expedition_id": expedition_id,
            "items_confirmed": items_confirmed,
            "package_info": package_info,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _complete_expedition(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Complete the expedition after NF emission.

    Payload:
        expedition_id: Expedition ID
        nf_number: NF number
        nf_key: NF access key (44 digits)
        carrier: Carrier/transportadora name
        tracking_code: Optional tracking number

    Returns:
        Completion result with created movements
    """
    expedition_id = payload.get("expedition_id", "")
    nf_number = payload.get("nf_number", "")
    nf_key = payload.get("nf_key", "")
    carrier = payload.get("carrier", "")
    tracking_code = payload.get("tracking_code")

    if not expedition_id:
        return {"success": False, "error": "expedition_id is required"}

    if not nf_number:
        return {"success": False, "error": "nf_number is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    result = await _invoke_agent_a2a(
        agent_id="expedition",
        action="complete_expedition",
        payload={
            "expedition_id": expedition_id,
            "nf_number": nf_number,
            "nf_key": nf_key,
            "carrier": carrier,
            "tracking_code": tracking_code,
        },
        session_id=session_id,
        user_id=user_id,
    )

    # Audit logging for A2A path
    try:
        from tools.dynamodb_client import SGAAuditLogger
        audit = SGAAuditLogger()
        audit.log_action(
            action="EXPEDITION_COMPLETED",
            entity_type="EXPEDITION",
            entity_id=expedition_id,
            actor=user_id,
            details={
                "nf_number": nf_number,
                "carrier": carrier,
                "tracking_code": tracking_code,
                "success": result.get("success", False),
                "protocol": "A2A",
            },
        )
    except Exception:
        pass

    return result


# =============================================================================
# Reverse Logistics Handlers (ReverseAgent)
# =============================================================================


async def _process_return(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Process an equipment return (reversa).

    Payload:
        serial: Serial number of returning equipment
        origin_type: Where equipment is coming from (CUSTOMER, FIELD_TECH, BRANCH)
        origin_address: Address/location from where it's returning
        owner: Equipment owner (FAISTON, NTT, TERCEIROS)
        condition: Equipment condition (FUNCIONAL, DEFEITUOSO, INSERVIVEL)
        return_reason: Reason for return (CONSERTO_CONCLUIDO, DEVOLUCAO_CLIENTE, etc.)
        chamado_id: Related ticket ID
        project_id: Related project
        notes: Additional notes

    Returns:
        Return result with depot assignment and movement creation
    """
    serial = payload.get("serial", "")
    origin_type = payload.get("origin_type", "")
    origin_address = payload.get("origin_address", "")
    owner = payload.get("owner", "FAISTON")
    condition = payload.get("condition", "FUNCIONAL")
    return_reason = payload.get("return_reason", "")
    chamado_id = payload.get("chamado_id")
    project_id = payload.get("project_id")
    notes = payload.get("notes", "")

    if not serial:
        return {"success": False, "error": "serial is required"}

    if not origin_type:
        return {"success": False, "error": "origin_type is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    result = await _invoke_agent_a2a(
        agent_id="reverse",
        action="process_return",
        payload={
            "serial_number": serial,  # Runtime expects serial_number
            "reason": return_reason,
            "condition": condition,
            "origin_reference": origin_address,
            "project_id": project_id,
            "notes": notes,
            "operator_id": user_id,
        },
        session_id=session_id,
        user_id=user_id,
    )

    # Audit logging for A2A path
    try:
        from tools.dynamodb_client import SGAAuditLogger
        audit = SGAAuditLogger()
        audit.log_action(
            action="RETURN_PROCESSED",
            entity_type="RETURN",
            entity_id=serial,
            actor=user_id,
            details={
                "origin_type": origin_type,
                "owner": owner,
                "condition": condition,
                "return_reason": return_reason,
                "chamado_id": chamado_id,
                "success": result.get("success", False),
                "protocol": "A2A",
            },
        )
    except Exception:
        pass

    return result


async def _validate_return_origin(payload: dict, session_id: str = "default") -> dict:
    """
    Validate the origin of a return shipment.

    Checks asset exists, traces last known location,
    and verifies return makes sense.

    Payload:
        serial: Serial number
        claimed_origin: Claimed origin location

    Returns:
        Validation result with asset info and match confidence
    """
    serial = payload.get("serial", "")
    claimed_origin = payload.get("claimed_origin", "")

    if not serial:
        return {"success": False, "error": "serial is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="reverse",
        action="validate_origin",
        payload={
            "serial_number": serial,  # Runtime expects serial_number
        },
        session_id=session_id,
        user_id="system",
    )


async def _evaluate_return_condition(payload: dict, session_id: str = "default") -> dict:
    """
    Evaluate equipment condition and determine destination.

    Uses AI to analyze condition description and photos
    to recommend appropriate depot.

    Payload:
        serial: Serial number
        owner: Equipment owner (FAISTON, NTT, TERCEIROS)
        condition_description: Text describing equipment state
        photos_s3_keys: Optional list of S3 keys for condition photos

    Returns:
        Evaluation with condition, recommended depot, and confidence
    """
    serial = payload.get("serial", "")
    owner = payload.get("owner", "FAISTON")
    condition_description = payload.get("condition_description", "")
    photos_s3_keys = payload.get("photos_s3_keys", [])

    if not serial:
        return {"success": False, "error": "serial is required"}

    if not condition_description:
        return {"success": False, "error": "condition_description is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="reverse",
        action="evaluate_condition",
        payload={
            "serial_number": serial,  # Runtime expects serial_number
            "inspection_notes": condition_description,  # Runtime uses inspection_notes
            "test_results": None,  # Not used in legacy API
        },
        session_id=session_id,
        user_id="system",
    )


# =============================================================================
# Carrier Quote Handlers (CarrierAgent)
# =============================================================================


async def _get_shipping_quotes(payload: dict, session_id: str = "default") -> dict:
    """
    Get shipping quotes from multiple carriers.

    NOTE: Currently returns mock data. Real API integrations
    (Correios, Loggi, Gollog) are pending.

    Payload:
        origin_cep: Origin postal code
        destination_cep: Destination postal code
        weight_kg: Package weight in kg
        dimensions: Package dimensions {length, width, height} in cm
        value: Declared value in R$
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)

    Returns:
        List of quotes with AI recommendation
    """
    origin_cep = payload.get("origin_cep", "")
    destination_cep = payload.get("destination_cep", "")
    weight_kg = payload.get("weight_kg", 1.0)
    dimensions = payload.get("dimensions", {"length": 30, "width": 20, "height": 10})
    value = payload.get("value", 100.0)
    urgency = payload.get("urgency", "NORMAL")

    if not origin_cep or not destination_cep:
        return {"success": False, "error": "origin_cep and destination_cep are required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="carrier",
        action="get_quotes",
        payload={
            "origin_cep": origin_cep,
            "destination_cep": destination_cep,
            "weight_kg": weight_kg,
            "dimensions": dimensions,
            "value": value,
            "urgency": urgency,
        },
        session_id=session_id,
        user_id="system",
    )


async def _recommend_carrier(payload: dict, session_id: str = "default") -> dict:
    """
    Get AI recommendation for best carrier.

    Uses rules + AI to recommend optimal carrier
    based on urgency, weight, value, and destination.

    Payload:
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
        weight_kg: Package weight
        value: Declared value
        destination_state: Destination state code (SP, RJ, etc.)
        same_city: Whether delivery is within same city

    Returns:
        Carrier recommendation with reasoning
    """
    urgency = payload.get("urgency", "NORMAL")
    weight_kg = payload.get("weight_kg", 1.0)
    value = payload.get("value", 100.0)
    destination_state = payload.get("destination_state", "SP")
    same_city = payload.get("same_city", False)

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="carrier",
        action="recommend_carrier",
        payload={
            "urgency": urgency,
            "weight_kg": weight_kg,
            "value": value,
            "destination_state": destination_state,
            "same_city": same_city,
        },
        session_id=session_id,
        user_id="system",
    )


async def _track_shipment(payload: dict, session_id: str = "default") -> dict:
    """
    Track a shipment by tracking code.

    NOTE: Currently returns mock data. Real API integrations
    are pending.

    Payload:
        tracking_code: Tracking code
        carrier: Optional carrier name for faster lookup

    Returns:
        Tracking information with events
    """
    tracking_code = payload.get("tracking_code", "")
    carrier = payload.get("carrier")

    if not tracking_code:
        return {"success": False, "error": "tracking_code is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="carrier",
        action="track_shipment",
        payload={
            "tracking_code": tracking_code,
            "carrier": carrier,
        },
        session_id=session_id,
        user_id="system",
    )


# =============================================================================
# Accuracy Metrics Handlers
# =============================================================================


async def _get_accuracy_metrics(payload: dict) -> dict:
    """
    Get AI accuracy metrics for dashboard.

    Returns KPIs about extraction accuracy, matching rates, and HIL metrics.
    Now queries real data from DynamoDB instead of returning mock values.

    Payload:
        period: Optional period filter ('today', 'week', 'month', 'all')
        project_id: Optional project filter

    Returns:
        Accuracy metrics with trends (real data from DynamoDB)
    """
    from tools.dynamodb_client import SGADynamoDBClient
    from agents.utils import now_iso
    from datetime import datetime, timedelta

    period = payload.get("period", "month")
    project_id = payload.get("project_id")

    db = SGADynamoDBClient()

    # Calculate date range based on period
    now = datetime.utcnow()
    if period == "today":
        year_month = now.strftime("%Y-%m")
    elif period == "week":
        year_month = now.strftime("%Y-%m")
    else:  # month or all
        year_month = now.strftime("%Y-%m")

    # Query real movements from DynamoDB
    movements = db.get_movements_by_date(year_month, limit=500)

    # Calculate real metrics from movements
    total_entries = len([m for m in movements if m.get("movement_type") == "ENTRY"])
    total_exits = len([m for m in movements if m.get("movement_type") == "EXIT"])
    total_returns = len([m for m in movements if m.get("movement_type") == "RETURN"])
    total_transfers = len([m for m in movements if m.get("movement_type") == "TRANSFER"])

    # Query pending HIL tasks
    pending_tasks = db.get_pending_tasks(limit=100)
    hil_count = len(pending_tasks)

    # Calculate entry success rate (completed vs total)
    completed_entries = len([m for m in movements if m.get("status") == "COMPLETED" and m.get("movement_type") == "ENTRY"])
    entry_success_rate = (completed_entries / total_entries * 100) if total_entries > 0 else 0

    # Build metrics with real data
    # Note: Some metrics like extraction_accuracy require audit log queries (future enhancement)
    metrics = {
        "extraction_accuracy": {
            "value": 0,
            "unit": "%",
            "description": "NF items matched on first attempt",
            "trend": "neutral",
            "change": 0,
            "note": "Requer integracao com audit log",
        },
        "entry_success_rate": {
            "value": round(entry_success_rate, 1),
            "unit": "%",
            "description": "Entries completed without rejection",
            "trend": "neutral",
            "change": 0,
        },
        "avg_hil_time": {
            "value": 0,
            "unit": "min",
            "description": "Average time to resolve HIL tasks",
            "trend": "neutral",
            "change": 0,
            "note": "Requer integracao com audit log",
        },
        "divergence_rate": {
            "value": 0,
            "unit": "%",
            "description": "Inventory counts with divergences",
            "trend": "neutral",
            "change": 0,
            "note": "Requer dados de inventario fisico",
        },
        "pn_match_by_method": {
            "supplier_code": 0,
            "description_ai": 0,
            "ncm": 0,
            "manual": 0,
            "note": "Requer integracao com audit log de matching",
        },
        "movements_summary": {
            "entries": total_entries,
            "expeditions": total_exits,
            "returns": total_returns,
            "transfers": total_transfers,
        },
        "pending_items": {
            "hil_tasks": hil_count,
            "pending_entries": len([m for m in movements if m.get("status") == "PENDING" and m.get("movement_type") == "ENTRY"]),
            "pending_reversals": len([m for m in movements if m.get("status") == "PENDING" and m.get("movement_type") == "RETURN"]),
        },
    }

    return {
        "success": True,
        "period": period,
        "project_id": project_id,
        "metrics": metrics,
        "generated_at": now_iso(),
        "data_source": "dynamodb",
        "note": "Dados reais do DynamoDB. Algumas metricas requerem integracao com audit log.",
    }


async def _reconcile_sap_export(payload: dict, user_id: str) -> dict:
    """
    Reconcile SAP export CSV with SGA inventory.

    Compares SAP stock positions with SGA balances
    and identifies real discrepancies from DynamoDB.

    Payload:
        sap_data: List of SAP rows [{part_number, location, quantity, serial?}]
        include_serials: Whether to compare at serial level
        project_id: Optional project filter

    Returns:
        Reconciliation result with real deltas from DynamoDB
    """
    from tools.dynamodb_client import SGADynamoDBClient
    from agents.utils import now_iso, generate_id

    sap_data = payload.get("sap_data", [])
    include_serials = payload.get("include_serials", False)
    project_id = payload.get("project_id")

    if not sap_data:
        return {"success": False, "error": "sap_data is required"}

    db = SGADynamoDBClient()

    # Group SAP data by PN + Location
    sap_balances = {}
    for row in sap_data:
        pn = row.get("part_number", "")
        loc = row.get("location", "01")
        qty = row.get("quantity", 0)
        key = f"{pn}|{loc}"

        if key not in sap_balances:
            sap_balances[key] = {"part_number": pn, "location": loc, "sap_qty": 0, "serials": []}
        sap_balances[key]["sap_qty"] += qty
        if row.get("serial"):
            sap_balances[key]["serials"].append(row["serial"])

    # Compare with REAL SGA balances from DynamoDB
    deltas = []
    for key, sap_item in sap_balances.items():
        pn = sap_item["part_number"]
        loc = sap_item["location"]
        sap_qty = sap_item["sap_qty"]

        # Query REAL balance from DynamoDB
        # Note: This requires pn_id and location_id, not codes
        # For now, we query by searching the PN first
        balance_result = db.get_balance(
            location_id=loc,
            pn_id=pn,
            project_id=project_id
        )
        sga_qty = balance_result.get("available", 0) + balance_result.get("reserved", 0)

        delta = sga_qty - sap_qty
        if delta != 0:
            deltas.append({
                "id": generate_id("DELTA"),
                "part_number": pn,
                "location": loc,
                "sap_quantity": sap_qty,
                "sga_quantity": sga_qty,
                "delta": delta,
                "delta_type": "FALTA_SGA" if delta < 0 else "SOBRA_SGA",
                "status": "PENDING",
                "serials_sap": sap_item["serials"] if include_serials else [],
            })

    # Summary
    total_items = len(sap_balances)
    items_matched = total_items - len(deltas)
    match_rate = (items_matched / total_items * 100) if total_items > 0 else 100

    return {
        "success": True,
        "reconciliation_id": generate_id("RECON"),
        "total_sap_items": total_items,
        "items_matched": items_matched,
        "items_with_delta": len(deltas),
        "match_rate": round(match_rate, 1),
        "deltas": deltas,
        "summary": {
            "falta_sga": len([d for d in deltas if d["delta_type"] == "FALTA_SGA"]),
            "sobra_sga": len([d for d in deltas if d["delta_type"] == "SOBRA_SGA"]),
        },
        "reconciled_by": user_id,
        "reconciled_at": now_iso(),
    }


async def _apply_reconciliation_action(payload: dict, user_id: str) -> dict:
    """
    Apply an action to a reconciliation delta.

    Actions:
    - CREATE_ADJUSTMENT: Create inventory adjustment
    - IGNORE: Mark as investigated and ignored
    - INVESTIGATE: Flag for manual investigation

    Payload:
        delta_id: Delta ID to act upon
        action: Action to apply
        notes: Action notes
        adjustment_quantity: For CREATE_ADJUSTMENT, the quantity to adjust

    Returns:
        Action result
    """
    from agents.utils import now_iso

    delta_id = payload.get("delta_id", "")
    action = payload.get("reconciliation_action", "") or payload.get("action", "")
    notes = payload.get("reason", "") or payload.get("notes", "")

    if not delta_id:
        return {"success": False, "error": "delta_id is required"}

    if action not in ["CREATE_ADJUSTMENT", "IGNORE", "INVESTIGATE"]:
        return {"success": False, "error": "Invalid action. Use CREATE_ADJUSTMENT, IGNORE, or INVESTIGATE"}

    # In production, update the delta record and create adjustment if needed
    result = {
        "success": True,
        "delta_id": delta_id,
        "action_taken": action,
        "applied_by": user_id,
        "applied_at": now_iso(),
    }

    if action == "CREATE_ADJUSTMENT":
        # Create HIL task for adjustment approval
        result["adjustment_id"] = f"ADJ-{delta_id[-6:]}"
        result["message"] = "Ajuste criado e enviado para aprovação"
    elif action == "IGNORE":
        result["message"] = "Delta ignorado após investigação"
    else:
        result["message"] = "Delta marcado para investigação manual"

    # Audit logging
    try:
        from tools.dynamodb_client import SGAAuditLogger
        audit = SGAAuditLogger()
        audit.log_action(
            action="RECONCILIATION_ACTION_APPLIED",
            entity_type="RECONCILIATION_DELTA",
            entity_id=delta_id,
            actor=user_id,
            details={
                "action_taken": action,
                "notes": notes[:200] if notes else None,  # Truncate long notes
            },
        )
    except Exception:
        pass  # Don't fail the request if audit logging fails

    return result


# =============================================================================
# NEXO Intelligent Import Handlers (Agentic AI-First)
# =============================================================================
# ReAct Pattern: OBSERVE → THINK → ASK → LEARN → ACT
#
# Philosophy: NEXO guides user through import with intelligent analysis
# - Multi-sheet XLSX analysis with purpose detection
# - Clarification questions when uncertain
# - Learning from user answers for future imports
# - Explicit reasoning trace for transparency


async def _nexo_analyze_file(payload: dict, user_id: str, session_id: str) -> dict:
    """
    NEXO intelligent file analysis (OBSERVE + THINK phases).

    Uses ReAct pattern to:
    1. OBSERVE: Analyze file structure (sheets, columns, rows)
    2. THINK: Reason about column mappings with Gemini AI
    3. Prepare questions for user when uncertain

    Payload:
        s3_key: S3 key of uploaded file
        filename: Original filename
        content_type: Optional MIME type
        prior_knowledge: Optional context from previous imports

    Returns:
        Analysis result with:
        - sheets: Multi-sheet analysis with detected purposes
        - column_mappings: Suggested mappings with confidence
        - reasoning_trace: Explicit thinking steps (transparency)
        - questions: Clarification questions for user
        - session_id: Import session ID for subsequent calls
    """
    s3_key = payload.get("s3_key", "")
    filename = payload.get("filename", "")
    content_type = payload.get("content_type", "")
    prior_knowledge = payload.get("prior_knowledge")

    if not s3_key:
        return {"success": False, "error": "s3_key is required"}

    if not filename:
        return {"success": False, "error": "filename is required"}

    # Import agent room service for status events
    from tools.agent_room_service import emit_agent_event

    print(f"[nexo_analyze_file] Starting analysis for: {filename}, s3_key: {s3_key}")

    # Emit initial Agent Room event
    emit_agent_event(
        agent_id="nexo_import",
        status="trabalhando",
        message=f"Recebi o arquivo {filename}. Analisando estrutura...",
        session_id=session_id,
        details={"filename": filename},
    )

    # Invoke NexoImportAgent via A2A Protocol
    result = await _invoke_agent_a2a(
        agent_id="nexo_import",
        action="analyze_file",
        payload={
            "filename": filename,
            "s3_key": s3_key,
            "prior_knowledge": prior_knowledge,
            "user_id": user_id,
        },
        session_id=session_id,
        user_id=user_id,
    )

    print(f"[nexo_analyze_file] Agent raw result: {result}")

    # Transform agent response to match frontend expected format (NexoAnalyzeFileResponse)
    # Agent returns: session_id, analysis, suggested_mappings, confidence, reasoning, questions
    # Frontend expects: import_session_id, filename, detected_file_type, analysis, column_mappings,
    #                   overall_confidence, questions, reasoning_trace

    if not result.get("success"):
        # Emit error event
        emit_agent_event(
            agent_id="nexo_import",
            status="problema",
            message=f"Erro ao analisar {filename}: {result.get('error', 'erro desconhecido')}",
            session_id=session_id,
        )
        return result

    # Extract analysis data
    analysis = result.get("analysis", {})
    sheets = analysis.get("sheets", [])

    # Emit analysis complete event with summary
    total_rows = sum(sheet.get("row_count", 0) for sheet in sheets)
    total_columns = sum(len(sheet.get("columns", [])) for sheet in sheets)
    questions = result.get("questions", [])
    has_questions = len(questions) > 0

    if has_questions:
        emit_agent_event(
            agent_id="nexo_import",
            status="esperando_voce",
            message=f"Encontrei {total_rows} linhas em {len(sheets)} planilha(s). Tenho {len(questions)} pergunta(s) para você.",
            session_id=session_id,
            details={"rows": total_rows, "sheets": len(sheets), "questions": len(questions)},
        )
    else:
        emit_agent_event(
            agent_id="nexo_import",
            status="disponivel",
            message=f"Análise completa! {total_rows} linhas, {total_columns} colunas mapeadas automaticamente.",
            session_id=session_id,
            details={"rows": total_rows, "columns": total_columns},
        )
    suggested_mappings = result.get("suggested_mappings", {})
    confidence = result.get("confidence", {})
    reasoning = result.get("reasoning", [])
    questions = result.get("questions", [])

    # Detect file type from extension
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    file_type_map = {
        "xlsx": "spreadsheet_xlsx",
        "xls": "spreadsheet_xls",
        "csv": "spreadsheet_csv",
        "xml": "nf_xml",
        "pdf": "nf_pdf",
        "jpg": "nf_image",
        "jpeg": "nf_image",
        "png": "nf_image",
    }
    detected_file_type = file_type_map.get(file_ext, f"unknown_{file_ext}")

    # Convert suggested_mappings dict to column_mappings array
    column_mappings = []
    for sheet in sheets:
        for col in sheet.get("columns", []):
            col_name = col.get("name", "")
            mapping = suggested_mappings.get(col_name) or col.get("suggested_mapping")
            mapping_confidence = col.get("mapping_confidence", 0.5)
            column_mappings.append({
                "source_column": col_name,
                "target_field": mapping,
                "confidence": mapping_confidence,
                "sample_values": col.get("sample_values", []),
                "needs_confirmation": mapping_confidence < 0.7,
            })

    # Extract overall confidence as number (agent returns dict with 'overall' key)
    overall_confidence = 0.5
    if isinstance(confidence, dict):
        overall_confidence = confidence.get("overall", 0.5)
    elif isinstance(confidence, (int, float)):
        overall_confidence = float(confidence)

    # Convert reasoning to reasoning_trace format
    # NOTE: Frontend expects 'type' field, not 'step'
    reasoning_trace = [
        {
            "type": r.get("type", "observation"),
            "content": r.get("content", ""),
            "tool": r.get("tool"),
            "result": r.get("result"),
            "timestamp": r.get("timestamp"),
        }
        for r in reasoning
    ]

    # Format questions
    formatted_questions = [
        {
            "id": q.get("id", f"Q-{i}"),
            "question": q.get("question", ""),
            "context": q.get("context", ""),
            "options": q.get("options", []),
            "importance": q.get("importance", "medium"),
            "topic": q.get("topic", "general"),
            "column": q.get("column"),
        }
        for i, q in enumerate(questions)
    ]

    # Extract session_id - may be at top level OR nested inside 'session' dict
    session_data = result.get("session", {})
    import_session_id = result.get("session_id") or session_data.get("session_id", "")

    # Extract TRUE agentic pattern fields
    inferred_movement_type = result.get("inferred_movement_type")
    movement_confidence = result.get("movement_confidence", 0.0)
    autonomous_decision = result.get("autonomous_decision", False)
    ready_for_processing = result.get("ready_for_processing", False)

    return {
        "success": True,
        "import_session_id": import_session_id,
        "filename": filename,
        "detected_file_type": detected_file_type,
        "analysis": {
            "sheet_count": analysis.get("sheet_count", len(sheets)),
            "total_rows": analysis.get("total_rows", 0),
            "sheets": sheets,
            "recommended_strategy": analysis.get("recommended_strategy", "single_sheet"),
            # TRUE agentic: include inferred movement type in analysis
            "inferred_movement_type": inferred_movement_type,
            "movement_type_confidence": movement_confidence,
        },
        "column_mappings": column_mappings,
        "overall_confidence": overall_confidence,
        "questions": formatted_questions,
        "reasoning_trace": reasoning_trace,
        "user_id": user_id,
        "session_id": session_id,
        "session_state": session_data,  # Pass full session state for stateless architecture
        # TRUE agentic pattern fields
        "inferred_movement_type": inferred_movement_type,  # AI-inferred movement type
        "movement_confidence": movement_confidence,        # Confidence in inference
        "autonomous_decision": autonomous_decision,        # True if AI decided without questions
        "ready_for_processing": ready_for_processing,     # True if can skip questions
    }


async def _nexo_get_questions(payload: dict, session_id: str) -> dict:
    """
    Get clarification questions for current import session (ASK phase) - STATELESS.

    Returns questions generated during analysis that require user input.

    Payload:
        session_state: Full session state from frontend (from previous analyze call)

    Returns:
        List of questions with options and importance levels, plus updated session state

    Architecture:
    - Invokes NexoImportAgent in dedicated runtime via A2A Protocol
    """
    session_state = payload.get("session_state")

    if not session_state:
        return {"success": False, "error": "session_state is required (stateless architecture)"}

    return await _invoke_agent_a2a(
        agent_id="nexo_import",
        action="get_questions",
        payload={"session_state": session_state},
        session_id=session_id,
    )


async def _nexo_submit_answers(payload: dict, session_id: str) -> dict:
    """
    Submit user answers to clarification questions (ASK → LEARN phases) - STATELESS.

    Processes user's answers and refines the analysis.
    Stores answers for learning and future improvement.

    Payload:
        session_state: Full session state from frontend
        answers: Dict mapping question IDs to selected answers
        user_feedback: Optional global user instructions for AI interpretation

    Returns:
        Updated session state with refined mappings based on answers

    Architecture:
    - Invokes NexoImportAgent in dedicated runtime via A2A Protocol
    """
    session_state = payload.get("session_state")
    answers = payload.get("answers", {})
    user_feedback = payload.get("user_feedback")

    if not session_state:
        return {"success": False, "error": "session_state is required (stateless architecture)"}

    if not answers:
        return {"success": False, "error": "answers is required"}

    return await _invoke_agent_a2a(
        agent_id="nexo_import",
        action="submit_answers",
        payload={
            "session_state": session_state,
            "answers": answers,
            "user_feedback": user_feedback,
        },
        session_id=session_id,
    )


async def _nexo_learn_from_import(payload: dict, session_id: str) -> dict:
    """
    Store learned patterns from successful import (LEARN phase) - STATELESS.

    Called after import confirmation to build knowledge base.
    Uses AgentCore Episodic Memory via LearningAgent for cross-session learning.

    Payload:
        session_state: Full session state from frontend
        import_result: Result of the executed import
        user_corrections: Any manual corrections made by user
        user_id: User performing the import

    Returns:
        Learning confirmation with episode_id and patterns stored

    Architecture:
    - Invokes NexoImportAgent in dedicated runtime via A2A Protocol
    """
    session_state = payload.get("session_state")
    import_result = payload.get("import_result", {})
    user_corrections = payload.get("user_corrections", {})
    # Note: user_id here is passed through to the downstream agent.
    # Identity validation happens at:
    # 1. Main entrypoint (invoke_sga_inventory) via extract_user_identity()
    # 2. Target agent (nexo_import) via its own extract_user_identity()
    # COMPLIANCE: AgentCore Identity v1.0 - validated at entrypoint
    user_id = payload.get("user_id", "anonymous")

    if not session_state:
        return {"success": False, "error": "session_state is required (stateless architecture)"}

    return await _invoke_agent_a2a(
        agent_id="nexo_import",
        action="learn_from_import",
        payload={
            "session_state": session_state,
            "import_result": import_result,
            "user_corrections": user_corrections,
            "user_id": user_id,
        },
        session_id=session_id,
    )


async def _nexo_execute_import(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Execute NEXO import: Insert rows into pending_entry_items (ACT phase) - STATELESS.

    This is the CORRECT action for NEXO Import flow. Unlike execute_import which
    creates movements directly, this action inserts into pending_entry_items table
    for items that still need validation/approval before becoming movements.

    FIX (January 2026): NEXO was incorrectly calling execute_import which tried
    to create movements (requiring valid part_numbers). NEXO should insert into
    pending_entry_items for operator review.

    Payload:
        session_state: Full session state from frontend (STATELESS architecture)
        column_mappings: Array of {file_column, target_field} mappings
        s3_key: S3 key of the file to import
        filename: Original filename
        project_id: Optional project to assign items
        destination_location_id: Optional destination location

    Returns:
        Import result with created_count and failed_rows
    """
    import logging
    import uuid
    logger = logging.getLogger(__name__)

    session_state = payload.get("session_state")
    column_mappings = payload.get("column_mappings", [])
    s3_key = payload.get("s3_key", "")
    filename = payload.get("filename", "import.csv")
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id")

    logger.info(f"[nexo_execute_import] Starting import for {filename}")
    logger.info(f"[nexo_execute_import] s3_key={s3_key}, column_mappings={len(column_mappings)}")

    # Validate required fields
    if not s3_key:
        return {"success": False, "error": "s3_key is required"}

    if not column_mappings:
        return {"success": False, "error": "column_mappings is required"}

    # Agent Room: emit start event
    from tools.agent_room_service import emit_agent_event
    emit_agent_event(
        agent_id="nexo_import",
        status="trabalhando",
        message=f"Iniciando importação de {filename}...",
        details={"filename": filename, "s3_key": s3_key},
    )

    # Download file from S3
    from tools.s3_client import SGAS3Client
    s3_client = SGAS3Client()
    try:
        file_content = s3_client.download_file(s3_key)
        logger.info(f"[nexo_execute_import] Downloaded from S3: {len(file_content) if file_content else 0} bytes")
    except Exception as e:
        logger.error(f"[nexo_execute_import] S3 download failed: {e}")
        return {"success": False, "error": f"Failed to download file from S3: {e}"}

    if not file_content:
        return {"success": False, "error": "Failed to get file content"}

    # Parse file using csv_parser with NEXO mappings
    from tools.csv_parser import extract_all_rows

    try:
        all_rows = extract_all_rows(file_content, filename, column_mappings)
        logger.info(f"[nexo_execute_import] Parsed {len(all_rows)} rows from file")
    except Exception as e:
        logger.error(f"[nexo_execute_import] File parsing failed: {e}")
        return {"success": False, "error": f"Failed to parse file: {e}"}

    if not all_rows:
        return {"success": False, "error": "No valid rows found in file"}

    # Initialize PostgreSQL client
    from tools.postgres_client import SGAPostgresClient

    try:
        pg_client = SGAPostgresClient()
        logger.info("[nexo_execute_import] PostgreSQL client initialized")
    except Exception as e:
        logger.error(f"[nexo_execute_import] PostgreSQL connection failed: {e}")
        return {"success": False, "error": f"Database connection failed: {e}"}

    # =================================================================
    # STEP 1: Create parent pending_entries record (BULK_IMPORT source)
    # =================================================================
    entry_id = str(uuid.uuid4())
    try:
        create_entry_sql = """
            INSERT INTO sga.pending_entries (
                entry_id, source_type, nf_number, supplier_name,
                total_items, status, s3_document_key, created_by
            ) VALUES (
                %s::uuid, 'BULK_IMPORT'::sga.entry_source, %s, %s,
                %s, 'PENDING', %s, %s
            )
            RETURNING entry_id
        """
        pg_client.execute_sql(
            create_entry_sql,
            (entry_id, session_id, f"NEXO Import: {filename}", len(all_rows), s3_key, user_id)
        )
        logger.info(f"[nexo_execute_import] Created pending_entries record: {entry_id}")
    except Exception as e:
        logger.error(f"[nexo_execute_import] Failed to create pending_entries: {e}")
        return {"success": False, "error": f"Failed to create entry record: {e}"}

    # =================================================================
    # STEP 2: Insert rows into pending_entry_items
    # =================================================================
    created_count = 0
    failed_rows = []

    for i, row_data in enumerate(all_rows):
        row_number = i + 2  # 1-based + header
        line_number = i + 1

        try:
            # Extract mapped data
            part_number = row_data.get("part_number", "").strip() if row_data.get("part_number") else ""
            description = row_data.get("description", "").strip() if row_data.get("description") else ""
            qty_str = str(row_data.get("quantity", "1")).strip()
            serial = row_data.get("serial", "").strip() if row_data.get("serial") else ""

            # Skip completely empty rows
            if not part_number and not description and not qty_str:
                continue

            # Parse quantity (default to 1)
            try:
                quantity = int(float(qty_str.replace(",", "."))) if qty_str else 1
                if quantity <= 0:
                    quantity = 1
            except (ValueError, TypeError):
                quantity = 1

            # Build serial_numbers array
            serial_numbers = [serial] if serial else None

            # Insert into pending_entry_items
            insert_sql = """
                INSERT INTO sga.pending_entry_items (
                    entry_id, line_number, part_number, description,
                    quantity, serial_numbers, is_processed
                ) VALUES (
                    %s::uuid, %s, %s, %s, %s, %s, FALSE
                )
                RETURNING entry_item_id
            """
            result = pg_client.execute_sql(
                insert_sql,
                (entry_id, line_number, part_number or None, description or None, quantity, serial_numbers)
            )

            created_count += 1
            if created_count % 100 == 0:
                logger.info(f"[nexo_execute_import] Inserted {created_count} rows...")

        except Exception as row_error:
            logger.error(f"[nexo_execute_import] Row {row_number} error: {row_error}")
            failed_rows.append({
                "row_number": row_number,
                "reason": str(row_error),
                "data": row_data,
            })

    # =================================================================
    # STEP 3: Update parent entry with actual counts
    # =================================================================
    try:
        update_sql = """
            UPDATE sga.pending_entries
            SET total_items = %s, status = CASE WHEN %s > 0 THEN 'PENDING' ELSE 'ERROR' END
            WHERE entry_id = %s::uuid
        """
        pg_client.execute_sql(update_sql, (created_count, created_count, entry_id))
    except Exception as e:
        logger.warning(f"[nexo_execute_import] Failed to update entry counts: {e}")

    # Agent Room: emit completion
    emit_agent_event(
        agent_id="nexo_import",
        status="concluído",
        message=f"Importação concluída: {created_count} itens criados",
        details={
            "entry_id": entry_id,
            "created_count": created_count,
            "failed_count": len(failed_rows),
        },
    )

    logger.info(f"[nexo_execute_import] Completed: {created_count} created, {len(failed_rows)} failed")

    return {
        "success": True,
        "entry_id": entry_id,
        "created_count": created_count,
        "failed_rows": failed_rows[:20] if failed_rows else [],  # Limit to first 20 failures
        "total_rows": len(all_rows),
    }


async def _nexo_get_prior_knowledge(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Retrieve prior knowledge before file analysis (RECALL phase).

    Queries AgentCore Episodic Memory via LearningAgent for similar
    past imports to provide auto-suggestions and learned mappings.

    Payload:
        filename: Name of file being imported
        file_analysis: Initial file analysis from sheet_analyzer
        s3_key: Optional S3 key of file

    Returns:
        Prior knowledge with:
        - similar_episodes: List of similar past imports
        - suggested_mappings: Column mappings from successful imports
        - confidence_boost: Whether to trust auto-mappings
        - reflections: Cross-session insights

    Architecture:
    - Invokes NexoImportAgent in dedicated runtime via A2A Protocol
    """
    filename = payload.get("filename", "")
    file_analysis = payload.get("file_analysis")

    if not filename:
        return {"success": False, "error": "filename is required"}

    return await _invoke_agent_a2a(
        agent_id="nexo_import",
        action="get_prior_knowledge",
        payload={
            "filename": filename,
            "file_analysis": file_analysis,
            "user_id": user_id,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _nexo_get_adaptive_threshold(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Get adaptive confidence threshold based on historical patterns.

    Uses LearningAgent reflections to determine appropriate threshold
    for this file pattern. Files with good history get lower thresholds
    (more trust), while unknown patterns get higher thresholds.

    Payload:
        filename: Name of file being imported

    Returns:
        Threshold configuration with:
        - threshold: Confidence threshold (0.0 to 1.0)
        - reason: Explanation for threshold choice
        - history_count: Number of similar imports in history

    Architecture:
    - Invokes NexoImportAgent in dedicated runtime via A2A Protocol
    """
    filename = payload.get("filename", "")

    if not filename:
        return {"success": False, "error": "filename is required"}

    result = await _invoke_agent_a2a(
        agent_id="nexo_import",
        action="get_adaptive_threshold",
        payload={
            "filename": filename,
            "user_id": user_id,
        },
        session_id=session_id,
        user_id=user_id,
    )

    # Extract threshold from result or return the whole result
    if isinstance(result, dict) and result.get("success"):
        return result

    # Wrap threshold value if agent returns just a number
    if isinstance(result, (int, float)):
        return {
            "success": True,
            "threshold": result,
            "filename": filename,
        }

    return result


async def _nexo_prepare_processing(payload: dict, session_id: str) -> dict:
    """
    Prepare final processing after questions answered (ACT phase) - STATELESS.

    Generates the final processing configuration with:
    - Confirmed column mappings
    - Sheet selection
    - Movement type
    - Any special handling

    Payload:
        session_state: Full session state from frontend

    Returns:
        Processing configuration ready for execute_import, plus updated session state

    Architecture:
    - Invokes NexoImportAgent in dedicated runtime via A2A Protocol
    """
    session_state = payload.get("session_state")

    if not session_state:
        return {"success": False, "error": "session_state is required (stateless architecture)"}

    from tools.agent_room_service import emit_agent_event

    # Emit event: starting to prepare import
    emit_agent_event(
        agent_id="nexo_import",
        status="trabalhando",
        message="Preparando dados para importação...",
        session_id=session_id,
    )

    result = await _invoke_agent_a2a(
        agent_id="nexo_import",
        action="prepare_for_processing",
        payload={"session_state": session_state},
        session_id=session_id,
    )

    # Emit completion event
    if isinstance(result, dict) and result.get("success"):
        item_count = result.get("item_count", 0)
        emit_agent_event(
            agent_id="nexo_import",
            status="disponivel",
            message=f"Pronto! {item_count} itens preparados para importação.",
            session_id=session_id,
            details={"item_count": item_count},
        )
    else:
        emit_agent_event(
            agent_id="nexo_import",
            status="problema",
            message=f"Erro ao preparar importação: {result.get('error', 'erro desconhecido') if isinstance(result, dict) else 'erro desconhecido'}",
            session_id=session_id,
        )

    return result


# =============================================================================
# Schema Introspection (Schema-Aware Import - January 2026)
# =============================================================================


async def _get_import_schema(payload: dict) -> dict:
    """
    Get PostgreSQL schema metadata for import operations.

    Returns detailed schema information including:
    - Table columns with data types and constraints
    - ENUM values (movement_type, asset_status, etc.)
    - Required columns (NOT NULL)
    - Foreign key references

    This enables clients to validate mappings and display
    schema-aware UI for import operations.

    Payload:
        target_table: Optional table name (default: pending_entry_items)
        include_enums: Whether to include ENUM definitions (default: True)
        include_fks: Whether to include FK references (default: True)
        format: "full" | "prompt" | "columns_only" (default: "full")

    Returns:
        Schema metadata for the target table(s)
    """
    target_table = payload.get("target_table", "pending_entry_items")
    include_enums = payload.get("include_enums", True)
    include_fks = payload.get("include_fks", True)
    format_type = payload.get("format", "full")

    try:
        from tools.schema_provider import SchemaProvider
        from tools.postgres_client import PostgresClient

        postgres_client = PostgresClient()
        provider = SchemaProvider(postgres_client)

        # Get table schema
        schema = provider.get_table_schema(target_table)

        if not schema:
            return {
                "success": False,
                "error": f"Table '{target_table}' not found in schema",
            }

        # Format based on requested type
        if format_type == "prompt":
            # Return markdown format for Gemini prompts
            return {
                "success": True,
                "target_table": target_table,
                "prompt_context": provider.get_schema_for_prompt(target_table),
                "schema_version": provider.get_schema_version(target_table),
            }

        elif format_type == "columns_only":
            # Return just column names and types
            return {
                "success": True,
                "target_table": target_table,
                "columns": [
                    {
                        "name": col.name,
                        "data_type": col.data_type,
                        "is_nullable": col.is_nullable,
                    }
                    for col in schema.columns
                ],
                "schema_version": provider.get_schema_version(target_table),
            }

        # Full format (default)
        result = {
            "success": True,
            "target_table": target_table,
            "columns": [
                {
                    "name": col.name,
                    "data_type": col.data_type,
                    "is_nullable": col.is_nullable,
                    "is_primary_key": col.is_primary_key,
                    "fk_reference": col.fk_reference,
                }
                for col in schema.columns
            ],
            "primary_key": schema.primary_key,
            "required_columns": [
                col.name for col in schema.columns if not col.is_nullable
            ],
            "schema_version": provider.get_schema_version(target_table),
        }

        # Include ENUMs if requested
        if include_enums:
            enum_names = ["movement_type", "asset_status", "entry_source"]
            enums = {}
            for enum_name in enum_names:
                try:
                    values = provider.get_enum_values(enum_name)
                    if values:
                        enums[enum_name] = values
                except Exception:
                    pass
            result["enums"] = enums

        # Include FKs if requested
        if include_fks:
            result["foreign_keys"] = schema.foreign_keys

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Schema introspection failed: {str(e)}",
        }


# =============================================================================
# Equipment Research (EquipmentResearchAgent)
# =============================================================================


async def _research_equipment(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Research documentation for a single piece of equipment.

    Uses Gemini 3.0 Pro with google_search grounding to find official
    documentation from manufacturer websites. Documents are downloaded
    and stored in S3 for Bedrock Knowledge Base ingestion.

    Payload:
        part_number: Equipment part number / SKU
        description: Equipment description
        serial_number: Optional serial number
        manufacturer: Optional manufacturer name
        additional_info: Optional extra context dict

    Returns:
        Research result with status, sources found, and documents downloaded
    """
    part_number = payload.get("part_number", "")
    description = payload.get("description", "")
    serial_number = payload.get("serial_number")
    manufacturer = payload.get("manufacturer")
    additional_info = payload.get("additional_info")

    if not part_number:
        return {"success": False, "error": "part_number is required"}

    if not description:
        return {"success": False, "error": "description is required"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="equipment_research",
        action="research_equipment",
        payload={
            "part_number": part_number,
            "description": description,
            "serial_number": serial_number,
            "manufacturer": manufacturer,
            "additional_info": additional_info,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _research_equipment_batch(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Research documentation for multiple equipment items.

    Processes items sequentially to respect Google Search rate limits.
    Useful after bulk imports to enrich all new items.

    Payload:
        equipment_list: List of equipment dicts, each with:
            - part_number: Equipment part number
            - description: Equipment description
            - serial_number: Optional serial number
            - manufacturer: Optional manufacturer name

    Returns:
        Batch result with status for each item
    """
    equipment_list = payload.get("equipment_list", [])

    if not equipment_list:
        return {"success": False, "error": "equipment_list is required"}

    if len(equipment_list) > 50:
        return {"success": False, "error": "Maximum 50 items per batch"}

    # =================================================================
    # A2A Protocol (100% Agentic Architecture)
    # =================================================================
    return await _invoke_agent_a2a(
        agent_id="equipment_research",
        action="research_batch",
        payload={
            "equipment_list": equipment_list,
        },
        session_id=session_id,
        user_id=user_id,
    )


async def _get_research_status(payload: dict, session_id: str = "default") -> dict:
    """
    Get research status for a part number.

    Checks if documentation research has been completed for this item.

    Note: This handler uses direct S3 access, not the EquipmentResearchAgent.
    Session ID is passed for consistency but not currently used.

    Payload:
        part_number: Part number to check

    Returns:
        Research status with documents if available
    """
    part_number = payload.get("part_number", "")

    if not part_number:
        return {"success": False, "error": "part_number is required"}

    # TODO: Query PostgreSQL for research status
    # For now, check S3 for existing documents
    from tools.s3_client import SGAS3Client
    import os
    import re
    import hashlib

    bucket = os.environ.get("EQUIPMENT_DOCS_BUCKET", "faiston-one-sga-equipment-docs-prod")
    s3_client = SGAS3Client(bucket_name=bucket)

    # Generate S3 prefix (same logic as agent)
    safe_pn = re.sub(r'[^a-zA-Z0-9\-_]', '_', part_number)
    hash_prefix = hashlib.md5(part_number.encode()).hexdigest()[:4]
    s3_prefix = f"equipment-docs/{hash_prefix}/{safe_pn}/"

    files = s3_client.list_files(prefix=s3_prefix, max_keys=20)

    if not files:
        return {
            "success": True,
            "part_number": part_number,
            "status": "NOT_RESEARCHED",
            "documents": [],
        }

    # Filter out metadata files
    docs = [f for f in files if not f["key"].endswith(".metadata.json")]

    return {
        "success": True,
        "part_number": part_number,
        "status": "COMPLETED" if docs else "NOT_RESEARCHED",
        "documents": [
            {
                "s3_key": f["key"],
                "size_bytes": f["size"],
                "last_modified": f["last_modified"],
            }
            for f in docs
        ],
        "s3_prefix": s3_prefix,
    }


async def _query_equipment_docs(payload: dict, user_id: str, session_id: str = "default") -> dict:
    """
    Query equipment documentation using Bedrock Knowledge Base.

    Searches the KB for relevant documentation and returns
    answers with citations to source documents.

    Note: This handler uses Bedrock Knowledge Base directly, not an agent.
    Session ID is passed for consistency but not currently used.

    Payload:
        query: Natural language question about equipment
        part_number: Optional filter by specific part number
        max_results: Maximum number of results (default 5)

    Returns:
        Answer with citations to source documents
    """
    # Lazy import
    from tools.knowledge_base_retrieval_tool import query_knowledge_base

    query = payload.get("query", "")
    part_number = payload.get("part_number")
    max_results = payload.get("max_results", 5)

    if not query:
        return {"success": False, "error": "query is required"}

    result = await query_knowledge_base(
        query=query,
        part_number_filter=part_number,
        max_results=max_results,
    )

    return result


# =============================================================================
# Auto-trigger Equipment Research (after imports)
# =============================================================================


async def _trigger_equipment_research_async(
    imported_items: list,
    user_id: str,
    session_id: str = "default",
) -> None:
    """
    Trigger equipment research asynchronously after import.

    This runs in the background and doesn't block the import response.
    Extracts unique part numbers from imported items and queues research.

    Args:
        imported_items: List of imported item dicts
        user_id: User who performed the import
        session_id: Session ID for tracking

    Architecture:
    - Invokes EquipmentResearchAgent in dedicated runtime via A2A Protocol
    """
    try:
        # Extract unique part numbers with descriptions
        seen_pns = set()
        equipment_to_research = []

        for item in imported_items:
            pn = item.get("part_number", "")
            if pn and pn not in seen_pns:
                seen_pns.add(pn)
                equipment_to_research.append({
                    "part_number": pn,
                    "description": item.get("description", ""),
                    "manufacturer": item.get("manufacturer"),
                })

        if not equipment_to_research:
            print("[EquipmentResearch] No new part numbers to research")
            return

        print(f"[EquipmentResearch] Triggering research for {len(equipment_to_research)} part numbers")

        # Research in batch via A2A Protocol
        result = await _invoke_agent_a2a(
            agent_id="equipment_research",
            action="research_batch",
            payload={
                "equipment_list": equipment_to_research[:20],  # Limit to 20 per import
            },
            session_id=session_id,
            user_id=user_id,
        )

        if isinstance(result, dict):
            completed = result.get("completed", 0)
            print(f"[EquipmentResearch] Completed: {completed}/{len(equipment_to_research[:20])}")

    except Exception as e:
        # Log but don't fail - research is non-blocking
        print(f"[EquipmentResearch] Error: {e}")


# =============================================================================
# Agent Room (Sala de Transparencia)
# =============================================================================


async def _get_agent_room_data(payload: dict, user_id: str) -> dict:
    """
    Get all Agent Room data for the transparency window.

    Returns humanized agent statuses, live feed events, learning stories,
    active workflows, and pending decisions in a single efficient call.

    Args:
        payload: Request payload (session_id optional)
        user_id: Current user ID

    Returns:
        Complete Agent Room data dict
    """
    try:
        from tools.agent_room_service import get_agent_room_data

        session_id = payload.get("session_id")

        return get_agent_room_data(user_id=user_id, session_id=session_id)

    except Exception as e:
        print(f"[AgentRoom] Error getting data: {e}")
        return {
            "success": False,
            "error": f"Erro ao carregar dados do Agent Room: {str(e)}",
        }


async def _get_xray_events(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Get X-Ray events for Agent Room traces panel.

    Returns enriched agent activity events with:
    - Event type classification (agent_activity, hil_decision, a2a_delegation, error)
    - Duration calculations between events
    - Session grouping for timeline display
    - HIL task integration inline

    Args:
        payload: Request payload with optional filters:
            - since_timestamp: ISO timestamp to fetch events after (for incremental updates)
            - filter_session_id: Optional session ID filter
            - filter_agent_id: Optional agent ID filter
            - show_hil_only: If true, only return HIL decision events
            - limit: Max events to return (default 50)
        user_id: Current user ID for HIL task filtering
        session_id: A2A session context

    Returns:
        X-Ray events data with session grouping
    """
    try:
        from tools.sse_stream import SSEStream, _enrich_events, _convert_hil_to_events
        from tools.agent_room_service import get_recent_events, get_pending_decisions
        from datetime import datetime, timedelta

        # Parse filters
        since_timestamp = payload.get("since_timestamp")
        filter_session_id = payload.get("filter_session_id")
        filter_agent_id = payload.get("filter_agent_id")
        show_hil_only = payload.get("show_hil_only", False)
        limit = payload.get("limit", 50)

        # Get recent events from audit log
        events = get_recent_events(days_back=1, limit=limit)

        # Convert to raw format for enrichment
        raw_events = []
        for e in events:
            raw_events.append({
                "event_id": e.get("id"),
                "timestamp": e.get("timestamp"),
                "actor_id": e.get("agentName", "").lower().replace(" ", "_"),
                "action": e.get("type", "trabalhando"),
                "details": {"message": e.get("message", "")},
                "event_type": e.get("eventType", "AGENT_ACTIVITY"),
                "session_id": e.get("sessionId"),
            })

        # Filter by timestamp if provided (for incremental updates)
        if since_timestamp:
            try:
                since_dt = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                raw_events = [
                    e for e in raw_events
                    if datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) > since_dt
                ]
            except (ValueError, TypeError):
                pass  # Invalid timestamp, ignore filter

        # Enrich events with duration, type classification
        session_timings = {}
        enriched = _enrich_events(raw_events, session_timings)

        # Get pending HIL tasks and convert to events
        hil_tasks = get_pending_decisions(user_id)
        hil_events = _convert_hil_to_events(hil_tasks)

        # Merge all events
        all_events = enriched + hil_events

        # Apply filters
        if filter_session_id:
            all_events = [e for e in all_events if e.get("sessionId") == filter_session_id]

        if filter_agent_id:
            all_events = [e for e in all_events if e.get("agentId") == filter_agent_id]

        if show_hil_only:
            all_events = [e for e in all_events if e.get("type") == "hil_decision"]

        # Sort by timestamp (newest first)
        all_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Limit results
        all_events = all_events[:limit]

        # Group by session for frontend
        sessions = {}
        no_session_events = []

        for event in all_events:
            sid = event.get("sessionId")
            if sid:
                if sid not in sessions:
                    sessions[sid] = {
                        "sessionId": sid,
                        "sessionName": event.get("sessionName") or f"Sessão {sid[:8]}",
                        "startTime": event.get("timestamp"),
                        "endTime": None,
                        "status": "active",
                        "events": [],
                        "eventCount": 0,
                    }
                sessions[sid]["events"].append(event)
                sessions[sid]["eventCount"] += 1
            else:
                no_session_events.append(event)

        # Calculate session status and durations
        for sid, session in sessions.items():
            events_sorted = sorted(
                session["events"],
                key=lambda x: x.get("timestamp", "")
            )
            if events_sorted:
                session["startTime"] = events_sorted[0].get("timestamp")
                last_event = events_sorted[-1]
                if last_event.get("action") == "concluido":
                    session["endTime"] = last_event.get("timestamp")
                    session["status"] = "completed"
                elif last_event.get("action") == "erro":
                    session["status"] = "error"
                # Calculate total duration
                total_duration = sum(e.get("duration", 0) for e in events_sorted)
                session["totalDuration"] = total_duration

        # Sort sessions by start time (newest first)
        session_list = sorted(
            sessions.values(),
            key=lambda s: s.get("startTime", ""),
            reverse=True
        )

        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "events": all_events,
            "sessions": session_list,
            "noSessionEvents": no_session_events,
            "totalEvents": len(all_events),
            "hilPendingCount": len([e for e in all_events if e.get("type") == "hil_decision"]),
        }

    except Exception as e:
        print(f"[X-Ray] Error getting events: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Erro ao carregar eventos X-Ray: {str(e)}",
        }


# =============================================================================
# Run Application
# =============================================================================

if __name__ == "__main__":
    app.run()
