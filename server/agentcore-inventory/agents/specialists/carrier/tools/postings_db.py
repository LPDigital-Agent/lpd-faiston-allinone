# =============================================================================
# Postings Database Tools
# =============================================================================
"""
DynamoDB operations for posting records management.

Architecture:
- Uses single-table design with GSI patterns for efficient queries
- Table: faiston-one-prod-sga-postings (injected via POSTINGS_TABLE env var)
- GSI1: StatusQuery - Query postings by status
- GSI2: UserQuery - Query postings by user
- GSI3: TrackingLookup - Lookup by tracking code

Key Patterns:
- PK: POSTING#{posting_id}
- SK: METADATA
- GSI1PK: STATUS#{status}
- GSI1SK: {created_at}#{posting_id}
- GSI2PK: USER#{user_id}
- GSI2SK: {created_at}#{posting_id}
- GSI3PK: TRACKING#{tracking_code}
- GSI3SK: METADATA

Status Flow:
- aguardando -> em_transito -> entregue
- aguardando -> cancelado (terminal)
- em_transito -> extraviado (terminal)

Important:
- Lazy imports for boto3 (Lambda cold start optimization)
- All operations include audit logging
- Order codes follow pattern: EXP-YYYY-NNNN
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "carrier"
audit = AgentAuditEmitter(agent_id=AGENT_ID)

# Lazy imports for cold start optimization
_dynamodb_resource = None
_postings_table = None


def _get_dynamodb_resource():
    """
    Get DynamoDB resource with lazy initialization.

    Returns:
        boto3 DynamoDB resource
    """
    global _dynamodb_resource
    if _dynamodb_resource is None:
        import boto3
        _dynamodb_resource = boto3.resource("dynamodb", region_name="us-east-2")
    return _dynamodb_resource


def _get_postings_table():
    """
    Get postings table with lazy initialization.

    Returns:
        boto3 DynamoDB Table resource
    """
    global _postings_table
    if _postings_table is None:
        table_name = os.environ.get("POSTINGS_TABLE", "faiston-one-prod-sga-postings")
        _postings_table = _get_dynamodb_resource().Table(table_name)
    return _postings_table


def _generate_posting_id() -> str:
    """
    Generate unique posting ID using UUID.

    Returns:
        UUID string for posting_id
    """
    import uuid
    return str(uuid.uuid4())


def _generate_order_code() -> str:
    """
    Generate sequential order code in format EXP-YYYY-NNNN.

    Uses atomic counter in DynamoDB to ensure uniqueness.
    Falls back to timestamp-based code if counter fails.

    Returns:
        Order code string (e.g., EXP-2026-0001)
    """
    year = datetime.utcnow().strftime("%Y")

    try:
        table = _get_postings_table()

        # Atomic increment of counter
        response = table.update_item(
            Key={"PK": "COUNTER#ORDER_CODE", "SK": f"YEAR#{year}"},
            UpdateExpression="SET counter_value = if_not_exists(counter_value, :zero) + :inc",
            ExpressionAttributeValues={":zero": 0, ":inc": 1},
            ReturnValues="UPDATED_NEW",
        )

        counter = int(response["Attributes"]["counter_value"])
        return f"EXP-{year}-{counter:04d}"

    except Exception as e:
        logger.warning(f"[postings_db] Counter failed, using timestamp: {e}")
        # Fallback to timestamp-based code
        timestamp = datetime.utcnow().strftime("%H%M%S")
        return f"EXP-{year}-T{timestamp}"


def _convert_to_decimal(obj: Any) -> Any:
    """
    Recursively convert float values to Decimal for DynamoDB compatibility.

    Args:
        obj: Any Python object

    Returns:
        Same structure with floats converted to Decimal
    """
    from decimal import Decimal

    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_to_decimal(i) for i in obj]
    return obj


def _convert_from_decimal(obj: Any) -> Any:
    """
    Recursively convert Decimal values to float for JSON serialization.

    Args:
        obj: Any Python object

    Returns:
        Same structure with Decimals converted to float
    """
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_from_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_from_decimal(i) for i in obj]
    return obj


# =============================================================================
# Status Constants and Transitions
# =============================================================================

VALID_STATUS_TRANSITIONS = {
    "aguardando": ["em_transito", "cancelado"],
    "em_transito": ["entregue", "extraviado"],
    "entregue": [],  # Terminal state
    "cancelado": [],  # Terminal state
    "extraviado": [],  # Terminal state
}

VALID_STATUSES = list(VALID_STATUS_TRANSITIONS.keys())

# Status descriptions (Portuguese)
POSTING_STATUSES = {
    "aguardando": "Aguardando coleta pela transportadora",
    "em_transito": "Em transito para o destinatario",
    "entregue": "Entregue ao destinatario",
    "cancelado": "Postagem cancelada",
    "extraviado": "Objeto extraviado",
}


# =============================================================================
# Tool Implementations
# =============================================================================


@trace_tool_call("sga_save_posting")
async def save_posting_tool(
    posting_data: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save a posting record to DynamoDB after successful VIPP creation.

    Creates a new posting record with auto-generated posting_id and order_code.
    Sets initial status to "aguardando" and creates GSI entries for efficient querying.

    Args:
        posting_data: Posting data containing:
            - tracking_code: Tracking code from carrier (required)
            - carrier: Carrier name (e.g., "Correios")
            - service: Service type (e.g., "SEDEX")
            - destination: Destination address dict
            - origin: Origin address dict
            - weight_grams: Package weight
            - dimensions: Package dimensions dict
            - declared_value: Declared value for insurance
            - price: Shipping price
            - delivery_days: Estimated delivery days
            - user_id: User who created the posting (required)
            - project_id: Related project ID (optional)
            - invoice_number: Related invoice number (optional)
            - notes: Additional notes (optional)
        session_id: Session ID for audit tracking

    Returns:
        Dict with:
            - success: True if saved successfully
            - posting_id: Generated posting ID
            - order_code: Generated order code (EXP-YYYY-NNNN)
            - posting: Complete posting record
            - error: Error message if failed
    """
    audit.working(
        message="Salvando registro de postagem no banco de dados",
        session_id=session_id,
    )

    try:
        # Validate required fields
        tracking_code = posting_data.get("tracking_code")
        user_id = posting_data.get("user_id")

        if not tracking_code:
            return {
                "success": False,
                "error": "tracking_code is required",
            }

        if not user_id:
            return {
                "success": False,
                "error": "user_id is required",
            }

        # Generate IDs
        posting_id = _generate_posting_id()
        order_code = _generate_order_code()

        now = datetime.utcnow()
        iso_now = now.isoformat() + "Z"

        # Build posting record
        posting_record = {
            # Primary Key
            "PK": f"POSTING#{posting_id}",
            "SK": "METADATA",

            # Core fields
            "posting_id": posting_id,
            "order_code": order_code,
            "tracking_code": tracking_code,
            "status": "aguardando",

            # Carrier info
            "carrier": posting_data.get("carrier", ""),
            "service": posting_data.get("service", ""),
            "service_code": posting_data.get("service_code", ""),

            # Address info
            "destination": posting_data.get("destination", {}),
            "origin": posting_data.get("origin", {}),

            # Package info
            "weight_grams": posting_data.get("weight_grams", 0),
            "dimensions": posting_data.get("dimensions", {}),
            "declared_value": posting_data.get("declared_value", 0),

            # Pricing
            "price": posting_data.get("price", 0),
            "delivery_days": posting_data.get("delivery_days", 0),
            "estimated_delivery": posting_data.get("estimated_delivery", ""),

            # References
            "user_id": user_id,
            "project_id": posting_data.get("project_id", ""),
            "invoice_number": posting_data.get("invoice_number", ""),
            "notes": posting_data.get("notes", ""),
            "urgency": posting_data.get("urgency", "NORMAL"),

            # Timestamps
            "created_at": iso_now,
            "updated_at": iso_now,

            # GSI Keys
            # GSI1: StatusQuery
            "GSI1PK": "STATUS#aguardando",
            "GSI1SK": f"{iso_now}#{posting_id}",

            # GSI2: UserQuery
            "GSI2PK": f"USER#{user_id}",
            "GSI2SK": f"{iso_now}#{posting_id}",

            # GSI3: TrackingLookup
            "GSI3PK": f"TRACKING#{tracking_code}",
            "GSI3SK": "METADATA",

            # Status history (event log)
            "status_history": [
                {
                    "status": "aguardando",
                    "timestamp": iso_now,
                    "actor": user_id,
                    "notes": "Postagem criada",
                }
            ],
        }

        # Convert floats to Decimal for DynamoDB
        posting_record = _convert_to_decimal(posting_record)

        # Save to DynamoDB
        table = _get_postings_table()
        table.put_item(Item=posting_record)

        audit.completed(
            message=f"Postagem salva: {order_code}",
            session_id=session_id,
            details={
                "posting_id": posting_id,
                "order_code": order_code,
                "tracking_code": tracking_code,
            },
        )

        return {
            "success": True,
            "posting_id": posting_id,
            "order_code": order_code,
            "posting": {
                "posting_id": posting_id,
                "order_code": order_code,
                "tracking_code": tracking_code,
                "status": "aguardando",
                "carrier": posting_data.get("carrier", ""),
                "service": posting_data.get("service", ""),
                "created_at": iso_now,
            },
        }

    except Exception as e:
        logger.error(f"[save_posting] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao salvar postagem",
            session_id=session_id,
            error=str(e),
        )
        return {"success": False, "error": str(e)}


@trace_tool_call("sga_get_postings")
async def get_postings_tool(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve postings from DynamoDB with optional filters.

    Query patterns:
    - If status provided: Query GSI1-StatusQuery
    - If user_id provided: Query GSI2-UserQuery
    - If neither: Scan with limit (use sparingly)

    Args:
        status: Filter by status (aguardando, em_transito, entregue, cancelado, extraviado)
        user_id: Filter by user ID
        limit: Maximum number of postings to return (default: 50, max: 100)
        session_id: Session ID for audit tracking

    Returns:
        Dict with:
            - success: True if query succeeded
            - postings: List of posting records
            - count: Number of postings returned
            - error: Error message if failed
    """
    audit.working(
        message="Consultando postagens no banco de dados",
        session_id=session_id,
    )

    try:
        table = _get_postings_table()
        limit = min(limit, 100)  # Cap at 100

        # Validate status if provided
        if status and status not in VALID_STATUSES:
            return {
                "success": False,
                "error": f"Invalid status. Valid values: {', '.join(VALID_STATUSES)}",
                "postings": [],
                "count": 0,
            }

        items = []

        if status:
            # Query GSI1-StatusQuery
            response = table.query(
                IndexName="GSI1-StatusQuery",
                KeyConditionExpression="GSI1PK = :pk",
                ExpressionAttributeValues={":pk": f"STATUS#{status}"},
                Limit=limit,
                ScanIndexForward=False,  # Newest first
            )
            items = response.get("Items", [])

        elif user_id:
            # Query GSI2-UserQuery
            response = table.query(
                IndexName="GSI2-UserQuery",
                KeyConditionExpression="GSI2PK = :pk",
                ExpressionAttributeValues={":pk": f"USER#{user_id}"},
                Limit=limit,
                ScanIndexForward=False,  # Newest first
            )
            items = response.get("Items", [])

        else:
            # Scan with filter (use sparingly)
            response = table.scan(
                FilterExpression="begins_with(PK, :pk_prefix)",
                ExpressionAttributeValues={":pk_prefix": "POSTING#"},
                Limit=limit,
            )
            items = response.get("Items", [])

        # Convert Decimal to float for JSON serialization
        postings = [_convert_from_decimal(item) for item in items]

        audit.completed(
            message=f"Encontradas {len(postings)} postagens",
            session_id=session_id,
            details={"count": len(postings), "status_filter": status, "user_filter": user_id},
        )

        return {
            "success": True,
            "postings": postings,
            "count": len(postings),
        }

    except Exception as e:
        logger.error(f"[get_postings] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao consultar postagens",
            session_id=session_id,
            error=str(e),
        )
        return {"success": False, "error": str(e), "postings": [], "count": 0}


@trace_tool_call("sga_update_posting_status")
async def update_posting_status_tool(
    posting_id: str,
    new_status: str,
    session_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update posting status with validation and audit logging.

    Valid status transitions:
    - aguardando -> em_transito, cancelado
    - em_transito -> entregue, extraviado
    - entregue, cancelado, extraviado -> (terminal states, no transitions)

    Args:
        posting_id: Posting ID to update
        new_status: New status value
        session_id: Session ID for audit tracking
        actor_id: ID of user/agent making the change (for audit)
        notes: Optional notes about the status change

    Returns:
        Dict with:
            - success: True if updated successfully
            - posting: Updated posting record
            - previous_status: Previous status value
            - error: Error message if failed
    """
    audit.working(
        message=f"Atualizando status da postagem {posting_id}",
        session_id=session_id,
    )

    try:
        # Validate new status
        if new_status not in VALID_STATUSES:
            return {
                "success": False,
                "error": f"Invalid status. Valid values: {', '.join(VALID_STATUSES)}",
            }

        table = _get_postings_table()

        # Get current posting
        response = table.get_item(
            Key={"PK": f"POSTING#{posting_id}", "SK": "METADATA"}
        )

        item = response.get("Item")
        if not item:
            return {
                "success": False,
                "error": f"Posting not found: {posting_id}",
            }

        current_status = item.get("status", "")

        # Validate status transition
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed_transitions:
            return {
                "success": False,
                "error": f"Invalid transition: {current_status} -> {new_status}. "
                         f"Allowed: {', '.join(allowed_transitions) or 'none (terminal state)'}",
                "current_status": current_status,
            }

        now = datetime.utcnow()
        iso_now = now.isoformat() + "Z"

        # Build status history entry
        status_entry = {
            "status": new_status,
            "timestamp": iso_now,
            "actor": actor_id or "system",
            "notes": notes or f"Status atualizado para {new_status}",
        }

        # Update posting
        update_response = table.update_item(
            Key={"PK": f"POSTING#{posting_id}", "SK": "METADATA"},
            UpdateExpression="""
                SET #status = :new_status,
                    #updated = :now,
                    #gsi1pk = :gsi1pk,
                    #gsi1sk = :gsi1sk,
                    #history = list_append(if_not_exists(#history, :empty_list), :entry)
            """,
            ExpressionAttributeNames={
                "#status": "status",
                "#updated": "updated_at",
                "#gsi1pk": "GSI1PK",
                "#gsi1sk": "GSI1SK",
                "#history": "status_history",
            },
            ExpressionAttributeValues={
                ":new_status": new_status,
                ":now": iso_now,
                ":gsi1pk": f"STATUS#{new_status}",
                ":gsi1sk": f"{iso_now}#{posting_id}",
                ":entry": [status_entry],
                ":empty_list": [],
            },
            ReturnValues="ALL_NEW",
        )

        updated_item = update_response.get("Attributes", {})

        # Convert Decimal to float
        updated_posting = _convert_from_decimal(updated_item)

        audit.completed(
            message=f"Status atualizado: {current_status} -> {new_status}",
            session_id=session_id,
            details={
                "posting_id": posting_id,
                "previous_status": current_status,
                "new_status": new_status,
            },
        )

        return {
            "success": True,
            "posting": updated_posting,
            "previous_status": current_status,
            "new_status": new_status,
        }

    except Exception as e:
        logger.error(f"[update_posting_status] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao atualizar status da postagem",
            session_id=session_id,
            error=str(e),
        )
        return {"success": False, "error": str(e)}


@trace_tool_call("sga_get_posting_by_tracking")
async def get_posting_by_tracking_tool(
    tracking_code: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Lookup posting by tracking code using GSI3.

    Args:
        tracking_code: Tracking code to search for
        session_id: Session ID for audit tracking

    Returns:
        Dict with:
            - success: True if operation succeeded
            - found: True if posting exists
            - posting: Posting record if found
            - error: Error message if failed
    """
    audit.working(
        message=f"Buscando postagem por rastreio: {tracking_code}",
        session_id=session_id,
    )

    try:
        table = _get_postings_table()

        # Query GSI3-TrackingLookup
        response = table.query(
            IndexName="GSI3-TrackingLookup",
            KeyConditionExpression="GSI3PK = :pk",
            ExpressionAttributeValues={":pk": f"TRACKING#{tracking_code}"},
            Limit=1,
        )

        items = response.get("Items", [])

        if not items:
            audit.completed(
                message=f"Postagem nao encontrada: {tracking_code}",
                session_id=session_id,
            )
            return {
                "success": True,
                "found": False,
                "posting": None,
                "message": f"No posting found for tracking code: {tracking_code}",
            }

        # Convert Decimal to float
        posting = _convert_from_decimal(items[0])

        audit.completed(
            message=f"Postagem encontrada: {posting.get('order_code', 'N/A')}",
            session_id=session_id,
            details={
                "posting_id": posting.get("posting_id"),
                "order_code": posting.get("order_code"),
                "status": posting.get("status"),
            },
        )

        return {
            "success": True,
            "found": True,
            "posting": posting,
        }

    except Exception as e:
        logger.error(f"[get_posting_by_tracking] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao buscar postagem por rastreio",
            session_id=session_id,
            error=str(e),
        )
        return {"success": False, "found": False, "error": str(e), "posting": None}


@trace_tool_call("sga_get_posting_by_id")
async def get_posting_by_id_tool(
    posting_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get posting by posting_id (direct primary key lookup).

    Args:
        posting_id: Posting ID to retrieve
        session_id: Session ID for audit tracking

    Returns:
        Dict with:
            - success: True if operation succeeded
            - found: True if posting exists
            - posting: Posting record if found
            - error: Error message if failed
    """
    audit.working(
        message=f"Buscando postagem: {posting_id}",
        session_id=session_id,
    )

    try:
        table = _get_postings_table()

        response = table.get_item(
            Key={"PK": f"POSTING#{posting_id}", "SK": "METADATA"}
        )

        item = response.get("Item")

        if not item:
            audit.completed(
                message=f"Postagem nao encontrada: {posting_id}",
                session_id=session_id,
            )
            return {
                "success": True,
                "found": False,
                "posting": None,
                "message": f"No posting found: {posting_id}",
            }

        # Convert Decimal to float
        posting = _convert_from_decimal(item)

        audit.completed(
            message=f"Postagem encontrada: {posting.get('order_code', 'N/A')}",
            session_id=session_id,
            details={
                "posting_id": posting_id,
                "order_code": posting.get("order_code"),
                "status": posting.get("status"),
            },
        )

        return {
            "success": True,
            "found": True,
            "posting": posting,
        }

    except Exception as e:
        logger.error(f"[get_posting_by_id] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao buscar postagem",
            session_id=session_id,
            error=str(e),
        )
        return {"success": False, "found": False, "error": str(e), "posting": None}


@trace_tool_call("sga_get_posting_by_order_code")
async def get_posting_by_order_code_tool(
    order_code: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get posting by order code (e.g., EXP-2026-0001).

    Uses scan with filter since order_code is not a primary key.
    For frequent lookups, consider adding a GSI.

    Args:
        order_code: Order code to search for
        session_id: Session ID for audit tracking

    Returns:
        Dict with:
            - success: True if operation succeeded
            - found: True if posting exists
            - posting: Posting record if found
            - error: Error message if failed
    """
    audit.working(
        message=f"Buscando postagem por codigo: {order_code}",
        session_id=session_id,
    )

    try:
        table = _get_postings_table()

        # Scan with filter for order_code
        response = table.scan(
            FilterExpression="order_code = :code",
            ExpressionAttributeValues={":code": order_code},
            Limit=1,
        )

        items = response.get("Items", [])

        if not items:
            audit.completed(
                message=f"Postagem nao encontrada: {order_code}",
                session_id=session_id,
            )
            return {
                "success": True,
                "found": False,
                "posting": None,
                "message": f"No posting found for order code: {order_code}",
            }

        # Convert Decimal to float
        posting = _convert_from_decimal(items[0])

        audit.completed(
            message=f"Postagem encontrada: {order_code}",
            session_id=session_id,
            details={
                "posting_id": posting.get("posting_id"),
                "tracking_code": posting.get("tracking_code"),
                "status": posting.get("status"),
            },
        )

        return {
            "success": True,
            "found": True,
            "posting": posting,
        }

    except Exception as e:
        logger.error(f"[get_posting_by_order_code] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao buscar postagem por codigo",
            session_id=session_id,
            error=str(e),
        )
        return {"success": False, "found": False, "error": str(e), "posting": None}


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Tools
    "save_posting_tool",
    "get_postings_tool",
    "update_posting_status_tool",
    "get_posting_by_tracking_tool",
    "get_posting_by_id_tool",
    "get_posting_by_order_code_tool",
    # Constants
    "POSTING_STATUSES",
    "VALID_STATUSES",
    "VALID_STATUS_TRANSITIONS",
]
