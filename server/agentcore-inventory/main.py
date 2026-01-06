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

USE_POSTGRES_MCP = os.environ.get("USE_POSTGRES_MCP", "false").lower() == "true"
AGENTCORE_GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
AGENTCORE_GATEWAY_ID = os.environ.get("AGENTCORE_GATEWAY_ID", "")

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
        # Use PostgreSQL via MCP Gateway
        from tools.mcp_gateway_client import MCPGatewayClientFactory
        from tools.gateway_adapter import GatewayPostgresAdapter

        def get_access_token():
            """
            Get JWT access token for Gateway authentication.

            In AgentCore Runtime, the token is available from request context.
            For local testing, can be set via environment variable.
            """
            # AgentCore injects token into environment during invocation
            return os.environ.get("AGENTCORE_ACCESS_TOKEN", "")

        mcp_client = MCPGatewayClientFactory.create_from_env(get_access_token)
        _database_adapter = GatewayPostgresAdapter(mcp_client)

        import logging
        logging.info("Database adapter: GatewayPostgresAdapter (PostgreSQL via MCP)")
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
    user_id = payload.get("user_id", "anonymous")
    session_id = getattr(context, "session_id", "default-session")

    # Debug logging to trace action routing
    print(f"[SGA Invoke] action={action}, user_id={user_id}, session_id={session_id}")

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
        # NF Processing (IntakeAgent)
        # =================================================================
        elif action == "get_nf_upload_url":
            return asyncio.run(_get_nf_upload_url(payload))

        elif action == "process_nf_upload":
            return asyncio.run(_process_nf_upload(payload, user_id))

        elif action == "validate_nf_extraction":
            return asyncio.run(_validate_nf_extraction(payload))

        elif action == "confirm_nf_entry":
            return asyncio.run(_confirm_nf_entry(payload, user_id))

        elif action == "process_scanned_nf_upload":
            return asyncio.run(_process_scanned_nf_upload(payload, user_id))

        elif action == "process_image_ocr":
            return asyncio.run(_process_image_ocr(payload, user_id))

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
        # Movements (EstoqueControlAgent)
        # =================================================================
        elif action == "create_movement":
            return asyncio.run(_create_movement(payload, user_id))

        elif action == "create_reservation":
            return asyncio.run(_create_reservation(payload, user_id))

        elif action == "cancel_reservation":
            return asyncio.run(_cancel_reservation(payload, user_id))

        elif action == "process_expedition":
            return asyncio.run(_process_expedition(payload, user_id))

        elif action == "create_transfer":
            return asyncio.run(_create_transfer(payload, user_id))

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
            return asyncio.run(_start_inventory_count(payload, user_id))

        elif action == "submit_count_result":
            return asyncio.run(_submit_count_result(payload, user_id))

        elif action == "analyze_divergences":
            return asyncio.run(_analyze_divergences(payload))

        elif action == "propose_adjustment":
            return asyncio.run(_propose_adjustment(payload, user_id))

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
            return asyncio.run(_preview_import(payload, user_id))

        elif action == "execute_import":
            return asyncio.run(_execute_import(payload, user_id))

        elif action == "validate_pn_mapping":
            return asyncio.run(_validate_pn_mapping(payload))

        # =================================================================
        # Smart Import (Auto-detect file type)
        # =================================================================
        elif action == "smart_import_upload":
            return asyncio.run(_smart_import_upload(payload, user_id))

        elif action == "generate_import_observations":
            return asyncio.run(_generate_import_observations(payload))

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

        elif action == "nexo_get_prior_knowledge":
            return asyncio.run(_nexo_get_prior_knowledge(payload, user_id))

        elif action == "nexo_get_adaptive_threshold":
            return asyncio.run(_nexo_get_adaptive_threshold(payload, user_id))

        # =================================================================
        # Expedition (ExpeditionAgent)
        # =================================================================
        elif action == "process_expedition_request":
            return asyncio.run(_process_expedition_request(payload, user_id))

        elif action == "verify_expedition_stock":
            return asyncio.run(_verify_expedition_stock(payload))

        elif action == "confirm_separation":
            return asyncio.run(_confirm_separation(payload, user_id))

        elif action == "complete_expedition":
            return asyncio.run(_complete_expedition(payload, user_id))

        # =================================================================
        # Reverse Logistics (ReverseAgent)
        # =================================================================
        elif action == "process_return":
            return asyncio.run(_process_return(payload, user_id))

        elif action == "validate_return_origin":
            return asyncio.run(_validate_return_origin(payload))

        elif action == "evaluate_return_condition":
            return asyncio.run(_evaluate_return_condition(payload))

        # =================================================================
        # Carrier Quotes (CarrierAgent)
        # =================================================================
        elif action == "get_shipping_quotes":
            return asyncio.run(_get_shipping_quotes(payload))

        elif action == "recommend_carrier":
            return asyncio.run(_recommend_carrier(payload))

        elif action == "track_shipment":
            return asyncio.run(_track_shipment(payload))

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
            index_name="GSI3",
            pk=f"{EntityPrefix.PROJECT}{project_id}",
            sk_prefix="ASSET#",
            limit=limit,
        )
    else:
        # Query all assets by status
        assets = db.query_gsi(
            index_name="GSI4",
            pk="STATUS#IN_STOCK",
            limit=limit,
        )

    return {
        "success": True,
        "assets": assets,
        "count": len(assets),
    }


async def _where_is_serial(payload: dict) -> dict:
    """
    Find the current location of a serialized asset.

    Natural language query: "Onde esta o serial XYZ?"
    """
    serial = payload.get("serial", "")
    if not serial:
        return {"success": False, "error": "Serial number required"}

    # Use EstoqueControlAgent for query
    from agents.estoque_control_agent import EstoqueControlAgent

    agent = EstoqueControlAgent()
    result = await agent.query_asset_location(serial_number=serial)

    return result


async def _get_balance(payload: dict) -> dict:
    """
    Get current balance for a part number at a location.

    Returns quantity available, reserved, and total.
    """
    part_number = payload.get("part_number", "")
    location_id = payload.get("location_id")
    project_id = payload.get("project_id")

    if not part_number:
        return {"success": False, "error": "part_number required"}

    from agents.estoque_control_agent import EstoqueControlAgent

    agent = EstoqueControlAgent()
    result = await agent.query_balance(
        part_number=part_number,
        location_id=location_id,
        project_id=project_id,
    )

    return result


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


async def _get_nf_upload_url(payload: dict) -> dict:
    """
    Get presigned URL for NF/document upload.

    Used by Smart Import to get S3 presigned URL before file upload.

    Payload:
        filename: Original filename
        content_type: MIME type of the file

    Returns:
        Dict with upload_url, s3_key, and expires_in
    """
    filename = payload.get("filename", "")
    content_type = payload.get("content_type", "application/octet-stream")

    if not filename:
        return {"success": False, "error": "filename is required"}

    # CRITICAL: Force reset S3 client to ensure SigV4 config is applied
    # This is needed because warm instances cache the old client
    # See: CLAUDE.md "S3 Presigned URL Issues - CORS 307 Redirect (CRITICAL)"
    import tools.s3_client as s3_module
    s3_module._s3_client = None  # Force recreation with SigV4 config
    print(f"[get_nf_upload_url] Reset S3 client - version {s3_module._MODULE_VERSION}")

    from agents.intake_agent import IntakeAgent

    agent = IntakeAgent()
    # Force reset agent's cached S3 client too
    agent._s3_client = None
    result = agent.get_upload_url(filename=filename, content_type=content_type)

    # Map 'key' to 's3_key' for frontend compatibility
    if result.get("success") and "key" in result:
        result["s3_key"] = result.pop("key")

    return result


async def _process_nf_upload(payload: dict, user_id: str) -> dict:
    """
    Process uploaded NF (PDF or XML).

    Extracts:
    - NF number, date, value
    - Items with quantities and unit prices
    - CFOP, NCM codes
    - Supplier information

    Returns extraction with confidence score.
    """
    s3_key = payload.get("s3_key", "")
    file_type = payload.get("file_type", "xml")
    project_id = payload.get("project_id", "")
    destination_location_id = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    if not s3_key:
        return {"success": False, "error": "s3_key required"}

    from agents.intake_agent import IntakeAgent

    agent = IntakeAgent()
    result = await agent.process_nf_upload(
        s3_key=s3_key,
        file_type=file_type,
        project_id=project_id,
        destination_location_id=destination_location_id,
        uploaded_by=user_id,
    )

    return result.to_dict()


async def _validate_nf_extraction(payload: dict) -> dict:
    """
    Validate NF extraction before confirmation.

    Checks:
    - Part numbers exist or need creation
    - Quantities are reasonable
    - Values match expected ranges
    """
    # TODO: Implement validation logic
    return {
        "success": True,
        "valid": False,
        "issues": [],
        "message": "Validation implemented in Sprint 2",
    }


async def _confirm_nf_entry(payload: dict, user_id: str) -> dict:
    """
    Confirm NF entry after user review.

    Creates:
    - ENTRY movement for each item
    - Updates balances
    - Audit log entry
    """
    entry_id = payload.get("entry_id", "")
    item_mappings = payload.get("item_mappings")
    notes = payload.get("notes")

    if not entry_id:
        return {"success": False, "error": "entry_id required"}

    from agents.intake_agent import IntakeAgent

    agent = IntakeAgent()
    result = await agent.confirm_entry(
        entry_id=entry_id,
        confirmed_by=user_id,
        item_mappings=item_mappings,
        notes=notes,
    )

    return result.to_dict()


async def _process_scanned_nf_upload(payload: dict, user_id: str) -> dict:
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

    Returns:
        Extraction result with confidence score and quality indicators
    """
    s3_key = payload.get("s3_key", "")
    project_id = payload.get("project_id", "")
    destination_location_id = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    if not s3_key:
        return {"success": False, "error": "s3_key required"}

    # Determine file type from S3 key
    file_type = "pdf"
    if s3_key.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
        file_type = "image"

    from agents.intake_agent import IntakeAgent

    agent = IntakeAgent()

    # Use the same processing flow but force scanned mode
    # by passing file_type as 'pdf' (triggers Vision)
    result = await agent.process_nf_upload(
        s3_key=s3_key,
        file_type="pdf",  # Forces PDF/scanned processing path
        project_id=project_id,
        destination_location_id=destination_location_id,
        uploaded_by=user_id,
    )

    response = result.to_dict()

    # Add scanned-specific metadata
    response["processing_type"] = "scanned_vision"
    response["original_file_type"] = file_type

    return response


# =============================================================================
# Image OCR Handler
# =============================================================================


async def _process_image_ocr(payload: dict, user_id: str) -> dict:
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

    Returns:
        Extraction result with confidence score
    """
    s3_key = payload.get("s3_key", "")
    project_id = payload.get("project_id", "")
    destination_location_id = payload.get("destination_location_id", "ESTOQUE_CENTRAL")

    if not s3_key:
        return {"success": False, "error": "s3_key required"}

    from agents.intake_agent import IntakeAgent

    agent = IntakeAgent()

    # Use file_type='image' to ensure Vision processing path
    result = await agent.process_nf_upload(
        s3_key=s3_key,
        file_type="image",  # Forces Vision OCR processing
        project_id=project_id,
        destination_location_id=destination_location_id,
        uploaded_by=user_id,
    )

    response = result.to_dict()
    response["processing_type"] = "image_vision_ocr"

    return response


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


async def _preview_sap_import(payload: dict, user_id: str) -> dict:
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
    """
    import base64
    from agents.import_agent import create_import_agent

    file_content_b64 = payload.get("file_content", "")
    filename = payload.get("filename", "sap_export.csv")
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id")
    full_asset_creation = payload.get("full_asset_creation", True)

    if not file_content_b64:
        return {"success": False, "error": "file_content is required"}

    try:
        file_content = base64.b64decode(file_content_b64)
    except Exception as e:
        return {"success": False, "error": f"Invalid base64 content: {e}"}

    agent = create_import_agent()
    result = await agent.preview_import(
        file_content=file_content,
        filename=filename,
        project_id=project_id,
        destination_location_id=destination_location_id,
        sap_format=True,  # Enable SAP-specific column detection
        full_asset_creation=full_asset_creation,
    )

    return result


async def _execute_sap_import(payload: dict, user_id: str) -> dict:
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
    """
    from agents.import_agent import create_import_agent

    import_id = payload.get("import_id", "")
    pn_overrides = payload.get("pn_overrides", {})
    full_asset_creation = payload.get("full_asset_creation", True)

    if not import_id:
        return {"success": False, "error": "import_id is required"}

    # Convert pn_overrides keys to int (JSON keys are strings)
    pn_overrides_int = {int(k): v for k, v in pn_overrides.items()}

    agent = create_import_agent()
    result = await agent.execute_sap_import(
        import_id=import_id,
        pn_overrides=pn_overrides_int,
        full_asset_creation=full_asset_creation,
        operator_id=user_id,
    )

    return result


# =============================================================================
# Movement Handlers
# =============================================================================


async def _create_movement(payload: dict, user_id: str) -> dict:
    """
    Create a generic inventory movement.

    Movement types: ENTRY, EXIT, TRANSFER, ADJUSTMENT, RETURN, DISCARD, LOSS
    """
    # TODO: Implement with EstoqueControlAgent
    return {
        "success": True,
        "movement_id": None,
        "message": "Movement creation implemented in Sprint 2",
    }


async def _create_reservation(payload: dict, user_id: str) -> dict:
    """
    Create a reservation for items.

    Reservations:
    - Block quantity from available balance
    - Have TTL for automatic expiration
    - Are linked to tickets/chamados
    """
    from agents.estoque_control_agent import EstoqueControlAgent

    agent = EstoqueControlAgent()
    result = await agent.create_reservation(
        part_number=payload.get("part_number", ""),
        quantity=payload.get("quantity", 1),
        project_id=payload.get("project_id", ""),
        chamado_id=payload.get("chamado_id"),
        serial_numbers=payload.get("serial_numbers"),
        source_location_id=payload.get("source_location_id", "ESTOQUE_CENTRAL"),
        destination_location_id=payload.get("destination_location_id"),
        requested_by=user_id,
        notes=payload.get("notes"),
        ttl_hours=payload.get("ttl_hours", 72),
    )

    return result.to_dict()


async def _cancel_reservation(payload: dict, user_id: str) -> dict:
    """Cancel an existing reservation."""
    reservation_id = payload.get("reservation_id", "")
    reason = payload.get("reason")

    if not reservation_id:
        return {"success": False, "error": "reservation_id required"}

    from agents.estoque_control_agent import EstoqueControlAgent

    agent = EstoqueControlAgent()
    result = await agent.cancel_reservation(
        reservation_id=reservation_id,
        cancelled_by=user_id,
        reason=reason,
    )

    return result.to_dict()


async def _process_expedition(payload: dict, user_id: str) -> dict:
    """
    Process an expedition (item exit).

    Flow:
    1. Validate reservation exists
    2. Create EXIT movement
    3. Update balances
    4. Clear reservation
    """
    from agents.estoque_control_agent import EstoqueControlAgent

    agent = EstoqueControlAgent()
    result = await agent.process_expedition(
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
    )

    return result.to_dict()


async def _create_transfer(payload: dict, user_id: str) -> dict:
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

    from agents.estoque_control_agent import EstoqueControlAgent

    agent = EstoqueControlAgent()
    result = await agent.create_transfer(
        part_number=part_number,
        quantity=quantity,
        source_location_id=source_location_id,
        destination_location_id=destination_location_id,
        project_id=project_id,
        serial_numbers=payload.get("serial_numbers"),
        requested_by=user_id,
        notes=payload.get("notes"),
    )

    return result.to_dict()


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


async def _start_inventory_count(payload: dict, user_id: str) -> dict:
    """
    Start a new inventory counting campaign.

    Creates a counting session for specified locations/items.
    """
    from agents.reconciliacao_agent import ReconciliacaoAgent

    agent = ReconciliacaoAgent()
    result = await agent.start_campaign(
        name=payload.get("name", ""),
        description=payload.get("description", ""),
        location_ids=payload.get("location_ids"),
        project_ids=payload.get("project_ids"),
        part_numbers=payload.get("part_numbers"),
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        created_by=user_id,
        require_double_count=payload.get("require_double_count", False),
    )

    return result.to_dict()


async def _submit_count_result(payload: dict, user_id: str) -> dict:
    """
    Submit counting result for an item.

    Records counted quantity for reconciliation.
    """
    campaign_id = payload.get("campaign_id", "")
    part_number = payload.get("part_number", "")
    location_id = payload.get("location_id", "")

    if not campaign_id or not part_number or not location_id:
        return {"success": False, "error": "campaign_id, part_number, and location_id required"}

    from agents.reconciliacao_agent import ReconciliacaoAgent

    agent = ReconciliacaoAgent()
    result = await agent.submit_count(
        campaign_id=campaign_id,
        part_number=part_number,
        location_id=location_id,
        counted_quantity=payload.get("counted_quantity", 0),
        counted_serials=payload.get("counted_serials"),
        counted_by=user_id,
        evidence_keys=payload.get("evidence_keys"),
        notes=payload.get("notes"),
    )

    return result.to_dict()


async def _analyze_divergences(payload: dict) -> dict:
    """
    Analyze divergences between counted and system quantities.

    Returns list of discrepancies with suggested actions.
    """
    campaign_id = payload.get("campaign_id", "")
    if not campaign_id:
        return {"success": False, "error": "campaign_id required"}

    from agents.reconciliacao_agent import ReconciliacaoAgent

    agent = ReconciliacaoAgent()
    return await agent.analyze_divergences(campaign_id=campaign_id)


async def _propose_adjustment(payload: dict, user_id: str) -> dict:
    """
    Propose an inventory adjustment based on counting.

    Always creates HIL task for approval.
    """
    campaign_id = payload.get("campaign_id", "")
    part_number = payload.get("part_number", "")
    location_id = payload.get("location_id", "")

    if not campaign_id or not part_number or not location_id:
        return {"success": False, "error": "campaign_id, part_number, and location_id required"}

    from agents.reconciliacao_agent import ReconciliacaoAgent

    agent = ReconciliacaoAgent()
    result = await agent.propose_adjustment(
        campaign_id=campaign_id,
        part_number=part_number,
        location_id=location_id,
        proposed_by=user_id,
        adjustment_reason=payload.get("adjustment_reason", ""),
    )

    return result.to_dict()


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


async def _preview_import(payload: dict, user_id: str) -> dict:
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
    """
    import base64
    from agents.import_agent import create_import_agent

    file_content_b64 = payload.get("file_content_base64", "")
    filename = payload.get("filename", "import.csv")
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id")

    if not file_content_b64:
        return {"success": False, "error": "file_content_base64 is required"}

    try:
        file_content = base64.b64decode(file_content_b64)
    except Exception as e:
        return {"success": False, "error": f"Invalid base64 content: {e}"}

    agent = create_import_agent()
    result = await agent.preview_import(
        file_content=file_content,
        filename=filename,
        project_id=project_id,
        destination_location_id=destination_location_id,
    )

    return result


async def _execute_import(payload: dict, user_id: str) -> dict:
    """
    Execute the import after preview/confirmation.

    Creates entry movements for all valid rows.

    Payload:
        import_id: Import session ID from preview
        file_content_base64: Base64-encoded file content
        filename: Original filename
        column_mappings: Confirmed column mappings [{file_column, target_field}]
        pn_overrides: Optional manual PN assignments {row_number: pn_id}
        project_id: Project to assign all items
        destination_location_id: Destination location

    Returns:
        Import result with created movements
    """
    import base64
    from agents.import_agent import create_import_agent

    import_id = payload.get("import_id", "")
    file_content_b64 = payload.get("file_content_base64", "")
    filename = payload.get("filename", "import.csv")
    column_mappings = payload.get("column_mappings", [])
    pn_overrides = payload.get("pn_overrides", {})
    project_id = payload.get("project_id")
    destination_location_id = payload.get("destination_location_id")

    if not import_id:
        return {"success": False, "error": "import_id is required"}

    if not file_content_b64:
        return {"success": False, "error": "file_content_base64 is required"}

    if not column_mappings:
        return {"success": False, "error": "column_mappings is required"}

    try:
        file_content = base64.b64decode(file_content_b64)
    except Exception as e:
        return {"success": False, "error": f"Invalid base64 content: {e}"}

    # Convert pn_overrides keys to int (JSON keys are strings)
    pn_overrides_int = {int(k): v for k, v in pn_overrides.items()}

    agent = create_import_agent()
    result = await agent.execute_import(
        import_id=import_id,
        file_content=file_content,
        filename=filename,
        column_mappings=column_mappings,
        pn_overrides=pn_overrides_int,
        project_id=project_id,
        destination_location_id=destination_location_id,
        operator_id=user_id,
    )

    return result


async def _validate_pn_mapping(payload: dict) -> dict:
    """
    Validate a part number mapping suggestion.

    Used by operator to confirm or override AI suggestions.

    Payload:
        description: Item description from file
        suggested_pn_id: Optional suggested PN to validate

    Returns:
        Validation result with alternative suggestions
    """
    from agents.import_agent import create_import_agent

    description = payload.get("description", "")
    suggested_pn_id = payload.get("suggested_pn_id")

    if not description:
        return {"success": False, "error": "description is required"}

    agent = create_import_agent()
    result = await agent.validate_pn_mapping(
        description=description,
        suggested_pn_id=suggested_pn_id,
    )

    return result


# =============================================================================
# Smart Import Handler (Auto-detect file type)
# =============================================================================


async def _smart_import_upload(payload: dict, user_id: str) -> dict:
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
    import base64

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
        from agents.intake_agent import IntakeAgent

        agent = IntakeAgent()
        result = await agent.process_nf_upload(
            s3_key=s3_key,
            file_type="pdf" if file_type == "image" else file_type,  # images use vision like PDFs
            project_id=project_id,
            destination_location_id=destination_location_id,
            uploaded_by=user_id,
        )

        # Convert to dict if needed
        if hasattr(result, "to_dict"):
            result = result.to_dict()

        # Add smart import metadata
        result["source_type"] = f"nf_{file_type}"
        result["detected_file_type"] = file_type
        result["file_type_label"] = get_file_type_label(file_type)

    elif file_type in ["csv", "xlsx"]:
        # Route to ImportAgent for spreadsheet processing
        from agents.import_agent import create_import_agent

        agent = create_import_agent()
        result = await agent.preview_import(
            file_content=file_data,
            filename=filename,
            project_id=project_id,
            destination_location_id=destination_location_id,
        )

        # Add smart import metadata
        result["source_type"] = "spreadsheet"
        result["detected_file_type"] = file_type
        result["file_type_label"] = get_file_type_label(file_type)

    elif file_type == "txt":
        # Route to ImportAgent for text processing with Gemini AI
        from agents.import_agent import create_import_agent

        agent = create_import_agent()

        # Decode text content
        try:
            text_content = file_data.decode("utf-8")
        except UnicodeDecodeError:
            text_content = file_data.decode("latin-1")

        result = await agent.process_text_import(
            file_content=text_content,
            filename=filename,
            project_id=project_id,
            destination_location_id=destination_location_id,
        )

        # Add smart import metadata
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


async def _generate_import_observations(payload: dict) -> dict:
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

    # Lazy import to respect AgentCore cold start limit
    from agents.observation_agent import ObservationAgent

    agent = ObservationAgent()
    result = agent.generate_observations(
        preview_data=preview_data,
        context=context,
    )

    return result


# =============================================================================
# Expedition Handlers (ExpeditionAgent)
# =============================================================================


async def _process_expedition_request(payload: dict, user_id: str) -> dict:
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
    from agents.expedition_agent import create_expedition_agent

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

    agent = create_expedition_agent()
    result = await agent.process_expedition_request(
        chamado_id=chamado_id,
        project_id=project_id,
        items=items,
        destination_client=destination_client,
        destination_address=destination_address,
        urgency=urgency,
        nature=nature,
        notes=notes,
        operator_id=user_id,
    )

    return result


async def _verify_expedition_stock(payload: dict) -> dict:
    """
    Verify stock availability for an item.

    Payload:
        pn_id: Part number ID
        serial: Optional serial number
        quantity: Quantity needed

    Returns:
        Verification result with availability status
    """
    from agents.expedition_agent import create_expedition_agent

    pn_id = payload.get("pn_id", "")
    serial = payload.get("serial")
    quantity = payload.get("quantity", 1)

    if not pn_id:
        return {"success": False, "error": "pn_id is required"}

    agent = create_expedition_agent()
    result = await agent.verify_stock(
        pn_id=pn_id,
        serial=serial,
        quantity=quantity,
    )

    return result


async def _confirm_separation(payload: dict, user_id: str) -> dict:
    """
    Confirm physical separation and packaging.

    Payload:
        expedition_id: Expedition ID
        items_confirmed: List of confirmed items with serials
        package_info: Packaging details (weight, dimensions)

    Returns:
        Confirmation result
    """
    from agents.expedition_agent import create_expedition_agent

    expedition_id = payload.get("expedition_id", "")
    items_confirmed = payload.get("items_confirmed", [])
    package_info = payload.get("package_info", {})

    if not expedition_id:
        return {"success": False, "error": "expedition_id is required"}

    agent = create_expedition_agent()
    result = await agent.confirm_separation(
        expedition_id=expedition_id,
        items_confirmed=items_confirmed,
        package_info=package_info,
        operator_id=user_id,
    )

    return result


async def _complete_expedition(payload: dict, user_id: str) -> dict:
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
    from agents.expedition_agent import create_expedition_agent

    expedition_id = payload.get("expedition_id", "")
    nf_number = payload.get("nf_number", "")
    nf_key = payload.get("nf_key", "")
    carrier = payload.get("carrier", "")
    tracking_code = payload.get("tracking_code")

    if not expedition_id:
        return {"success": False, "error": "expedition_id is required"}

    if not nf_number:
        return {"success": False, "error": "nf_number is required"}

    agent = create_expedition_agent()
    result = await agent.complete_expedition(
        expedition_id=expedition_id,
        nf_number=nf_number,
        nf_key=nf_key,
        carrier=carrier,
        tracking_code=tracking_code,
        operator_id=user_id,
    )

    return result


# =============================================================================
# Reverse Logistics Handlers (ReverseAgent)
# =============================================================================


async def _process_return(payload: dict, user_id: str) -> dict:
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
    from agents.reverse_agent import create_reverse_agent

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

    agent = create_reverse_agent()
    result = await agent.process_return(
        serial=serial,
        origin_type=origin_type,
        origin_address=origin_address,
        owner=owner,
        condition=condition,
        return_reason=return_reason,
        chamado_id=chamado_id,
        project_id=project_id,
        notes=notes,
        operator_id=user_id,
    )

    return result


async def _validate_return_origin(payload: dict) -> dict:
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
    from agents.reverse_agent import create_reverse_agent

    serial = payload.get("serial", "")
    claimed_origin = payload.get("claimed_origin", "")

    if not serial:
        return {"success": False, "error": "serial is required"}

    agent = create_reverse_agent()
    result = await agent.validate_origin(
        serial=serial,
        claimed_origin=claimed_origin,
    )

    return result


async def _evaluate_return_condition(payload: dict) -> dict:
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
    from agents.reverse_agent import create_reverse_agent

    serial = payload.get("serial", "")
    owner = payload.get("owner", "FAISTON")
    condition_description = payload.get("condition_description", "")
    photos_s3_keys = payload.get("photos_s3_keys", [])

    if not serial:
        return {"success": False, "error": "serial is required"}

    if not condition_description:
        return {"success": False, "error": "condition_description is required"}

    agent = create_reverse_agent()
    result = await agent.evaluate_condition(
        serial=serial,
        owner=owner,
        condition_description=condition_description,
        photos_s3_keys=photos_s3_keys,
    )

    return result


# =============================================================================
# Carrier Quote Handlers (CarrierAgent)
# =============================================================================


async def _get_shipping_quotes(payload: dict) -> dict:
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
    from agents.carrier_agent import create_carrier_agent

    origin_cep = payload.get("origin_cep", "")
    destination_cep = payload.get("destination_cep", "")
    weight_kg = payload.get("weight_kg", 1.0)
    dimensions = payload.get("dimensions", {"length": 30, "width": 20, "height": 10})
    value = payload.get("value", 100.0)
    urgency = payload.get("urgency", "NORMAL")

    if not origin_cep or not destination_cep:
        return {"success": False, "error": "origin_cep and destination_cep are required"}

    agent = create_carrier_agent()
    result = await agent.get_quotes(
        origin_cep=origin_cep,
        destination_cep=destination_cep,
        weight_kg=weight_kg,
        dimensions=dimensions,
        value=value,
        urgency=urgency,
    )

    return result


async def _recommend_carrier(payload: dict) -> dict:
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
    from agents.carrier_agent import create_carrier_agent

    urgency = payload.get("urgency", "NORMAL")
    weight_kg = payload.get("weight_kg", 1.0)
    value = payload.get("value", 100.0)
    destination_state = payload.get("destination_state", "SP")
    same_city = payload.get("same_city", False)

    agent = create_carrier_agent()
    result = await agent.recommend_carrier(
        urgency=urgency,
        weight_kg=weight_kg,
        value=value,
        destination_state=destination_state,
        same_city=same_city,
    )

    return result


async def _track_shipment(payload: dict) -> dict:
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
    from agents.carrier_agent import create_carrier_agent

    tracking_code = payload.get("tracking_code", "")
    carrier = payload.get("carrier")

    if not tracking_code:
        return {"success": False, "error": "tracking_code is required"}

    agent = create_carrier_agent()
    result = await agent.track_shipment(
        tracking_code=tracking_code,
        carrier=carrier,
    )

    return result


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

    # Download file from S3
    from tools.s3_client import SGAS3Client

    s3_client = SGAS3Client()
    try:
        file_data = s3_client.download_file(s3_key)
    except Exception as e:
        return {"success": False, "error": f"Failed to download file from S3: {e}"}

    # Lazy import to respect AgentCore cold start limit
    from agents.nexo_import_agent import NexoImportAgent

    agent = NexoImportAgent()
    result = await agent.analyze_file_intelligently(
        filename=filename,
        s3_key=s3_key,
        file_content=file_data,
        prior_knowledge=prior_knowledge,
    )

    # Transform agent response to match frontend expected format (NexoAnalyzeFileResponse)
    # Agent returns: session_id, analysis, suggested_mappings, confidence, reasoning, questions
    # Frontend expects: import_session_id, filename, detected_file_type, analysis, column_mappings,
    #                   overall_confidence, questions, reasoning_trace

    if not result.get("success"):
        return result

    # Extract analysis data
    analysis = result.get("analysis", {})
    sheets = analysis.get("sheets", [])
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
    reasoning_trace = [
        {
            "step": r.get("type", "observation"),
            "content": r.get("content", ""),
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

    return {
        "success": True,
        "import_session_id": result.get("session_id", ""),
        "filename": filename,
        "detected_file_type": detected_file_type,
        "analysis": {
            "sheet_count": analysis.get("sheet_count", len(sheets)),
            "total_rows": analysis.get("total_rows", 0),
            "sheets": sheets,
            "recommended_strategy": analysis.get("recommended_strategy", "single_sheet"),
        },
        "column_mappings": column_mappings,
        "overall_confidence": overall_confidence,
        "questions": formatted_questions,
        "reasoning_trace": reasoning_trace,
        "user_id": user_id,
        "session_id": session_id,
    }


async def _nexo_get_questions(payload: dict, session_id: str) -> dict:
    """
    Get clarification questions for current import session (ASK phase).

    Returns questions generated during analysis that require user input.

    Payload:
        import_session_id: Import session ID from analyze_file

    Returns:
        List of questions with options and importance levels
    """
    import_session_id = payload.get("import_session_id", "")

    if not import_session_id:
        return {"success": False, "error": "import_session_id is required"}

    from agents.nexo_import_agent import NexoImportAgent

    agent = NexoImportAgent()
    result = await agent.get_questions(session_id=import_session_id)

    return result


async def _nexo_submit_answers(payload: dict, session_id: str) -> dict:
    """
    Submit user answers to clarification questions (ASK → LEARN phases).

    Processes user's answers and refines the analysis.
    Stores answers for learning and future improvement.

    Payload:
        import_session_id: Import session ID
        answers: Dict mapping question IDs to selected answers

    Returns:
        Updated analysis with refined mappings based on answers
    """
    import_session_id = payload.get("import_session_id", "")
    answers = payload.get("answers", {})

    if not import_session_id:
        return {"success": False, "error": "import_session_id is required"}

    if not answers:
        return {"success": False, "error": "answers is required"}

    from agents.nexo_import_agent import NexoImportAgent

    agent = NexoImportAgent()
    result = await agent.submit_answers(
        session_id=import_session_id,
        answers=answers,
    )

    return result


async def _nexo_learn_from_import(payload: dict, session_id: str) -> dict:
    """
    Store learned patterns from successful import (LEARN phase).

    Called after import confirmation to build knowledge base.
    Uses AgentCore Episodic Memory via LearningAgent for cross-session learning.

    Payload:
        import_session_id: Import session ID
        import_result: Result of the executed import
        user_corrections: Any manual corrections made by user
        user_id: User performing the import

    Returns:
        Learning confirmation with episode_id and patterns stored
    """
    import_session_id = payload.get("import_session_id", "")
    import_result = payload.get("import_result", {})
    user_corrections = payload.get("user_corrections", {})
    user_id = payload.get("user_id", "anonymous")

    if not import_session_id:
        return {"success": False, "error": "import_session_id is required"}

    from agents.nexo_import_agent import NexoImportAgent

    agent = NexoImportAgent()
    result = await agent.learn_from_import(
        session_id=import_session_id,
        import_result=import_result,
        user_id=user_id,
        user_corrections=user_corrections,
    )

    return result


async def _nexo_get_prior_knowledge(payload: dict, user_id: str) -> dict:
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
    """
    filename = payload.get("filename", "")
    file_analysis = payload.get("file_analysis", {})

    if not filename:
        return {"success": False, "error": "filename is required"}

    if not file_analysis:
        return {"success": False, "error": "file_analysis is required"}

    from agents.nexo_import_agent import NexoImportAgent

    agent = NexoImportAgent()
    result = await agent.get_prior_knowledge(
        filename=filename,
        file_analysis=file_analysis,
        user_id=user_id,
    )

    return result


async def _nexo_get_adaptive_threshold(payload: dict, user_id: str) -> dict:
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
    """
    filename = payload.get("filename", "")

    if not filename:
        return {"success": False, "error": "filename is required"}

    from agents.nexo_import_agent import NexoImportAgent

    agent = NexoImportAgent()
    threshold = await agent.get_adaptive_threshold(
        filename=filename,
        user_id=user_id,
    )

    return {
        "success": True,
        "threshold": threshold,
        "filename": filename,
    }


async def _nexo_prepare_processing(payload: dict, session_id: str) -> dict:
    """
    Prepare final processing after questions answered (ACT phase).

    Generates the final processing configuration with:
    - Confirmed column mappings
    - Sheet selection
    - Movement type
    - Any special handling

    Payload:
        import_session_id: Import session ID

    Returns:
        Processing configuration ready for execute_import
    """
    import_session_id = payload.get("import_session_id", "")

    if not import_session_id:
        return {"success": False, "error": "import_session_id is required"}

    from agents.nexo_import_agent import NexoImportAgent

    agent = NexoImportAgent()
    result = await agent.prepare_for_processing(session_id=import_session_id)

    return result


# =============================================================================
# Run Application
# =============================================================================

if __name__ == "__main__":
    app.run()
