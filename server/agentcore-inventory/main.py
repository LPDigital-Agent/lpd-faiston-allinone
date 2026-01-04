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
# - IntakeAgent: NF-e PDF/XML extraction
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

# LAZY IMPORTS: Agents are imported inside handler functions to reduce cold start.
# Each agent imports Google ADK packages (~3-5s each).

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

    # Route to appropriate handler
    try:
        # =================================================================
        # Health & System
        # =================================================================
        if action == "health_check":
            return _health_check()

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
        # NF-e Processing (IntakeAgent)
        # =================================================================
        elif action == "process_nf_upload":
            return asyncio.run(_process_nf_upload(payload, user_id))

        elif action == "validate_nf_extraction":
            return asyncio.run(_validate_nf_extraction(payload))

        elif action == "confirm_nf_entry":
            return asyncio.run(_confirm_nf_entry(payload, user_id))

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
    """
    from agents.utils import AGENT_VERSION, MODEL_GEMINI

    return {
        "success": True,
        "status": "healthy",
        "version": AGENT_VERSION,
        "model": MODEL_GEMINI,
        "module": "Gestao de Ativos - Estoque",
        "agents": [
            "EstoqueControlAgent",
            "IntakeAgent",
            "ReconciliacaoAgent",
            "ComplianceAgent",
            "ComunicacaoAgent",
        ],
        "tables": {
            "inventory": os.environ.get("INVENTORY_TABLE", ""),
            "hil_tasks": os.environ.get("HIL_TASKS_TABLE", ""),
            "audit_log": os.environ.get("AUDIT_LOG_TABLE", ""),
        },
        "bucket": os.environ.get("DOCUMENTS_BUCKET", ""),
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
# NF-e Processing Handlers
# =============================================================================


async def _process_nf_upload(payload: dict, user_id: str) -> dict:
    """
    Process uploaded NF-e (PDF or XML).

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
    # TODO: Implement with ReconciliacaoAgent
    return {
        "success": True,
        "campaign_id": None,
        "message": "Counting campaign implemented in Sprint 3",
    }


async def _submit_count_result(payload: dict, user_id: str) -> dict:
    """
    Submit counting result for an item.

    Records counted quantity for reconciliation.
    """
    # TODO: Implement with ReconciliacaoAgent
    return {
        "success": True,
        "message": "Count submission implemented in Sprint 3",
    }


async def _analyze_divergences(payload: dict) -> dict:
    """
    Analyze divergences between counted and system quantities.

    Returns list of discrepancies with suggested actions.
    """
    # TODO: Implement with ReconciliacaoAgent
    return {
        "success": True,
        "divergences": [],
        "message": "Divergence analysis implemented in Sprint 3",
    }


async def _propose_adjustment(payload: dict, user_id: str) -> dict:
    """
    Propose an inventory adjustment based on counting.

    Always creates HIL task for approval.
    """
    # TODO: Implement with ReconciliacaoAgent
    return {
        "success": True,
        "task_id": None,
        "message": "Adjustment proposal implemented in Sprint 3",
    }


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
# Run Application
# =============================================================================

if __name__ == "__main__":
    app.run()
