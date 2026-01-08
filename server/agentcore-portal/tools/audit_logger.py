# =============================================================================
# Portal Audit Logger
# =============================================================================
# Lightweight audit logger for Portal agents.
# Logs to the same DynamoDB table as SGA Inventory: faiston-one-sga-audit-log-prod
#
# Uses lazy imports to minimize cold start impact on AgentCore Runtime.
#
# Event Types:
# - PORTAL_NEXO_CHAT
# - PORTAL_DAILY_SUMMARY
# - PORTAL_NEWS_FETCH
# - PORTAL_NEWS_SEARCH
# - PORTAL_DELEGATION_ACADEMY
# - PORTAL_DELEGATION_SGA
# =============================================================================

from typing import Dict, Any, Optional
from datetime import datetime
import os

# Lazy imports - boto3 imported only when needed
_dynamodb_resource = None


def _get_dynamodb_resource():
    """Get DynamoDB resource with lazy initialization."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        import boto3
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


def _get_audit_table() -> str:
    """Get audit log table name from environment."""
    return os.environ.get("AUDIT_LOG_TABLE", "faiston-one-sga-audit-log-prod")


def log_portal_event(
    event_type: str,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    success: bool = True,
) -> bool:
    """
    Log a Portal audit event to DynamoDB.

    Args:
        event_type: Type of event (PORTAL_NEXO_CHAT, PORTAL_NEWS_FETCH, etc.)
        actor_id: User ID performing the action
        entity_type: Entity type affected (CONVERSATION, NEWS, SUMMARY, etc.)
        entity_id: Entity identifier (session_id, category, etc.)
        action: Action performed (nexo_chat, get_tech_news, etc.)
        details: Additional safe-to-log details
        session_id: Optional session identifier
        success: Whether the operation succeeded (default: True)

    Returns:
        True if logging succeeded, False otherwise
    """
    try:
        import uuid

        now = datetime.utcnow()
        iso_now = now.isoformat() + "Z"
        date_key = now.strftime("%Y-%m-%d")
        event_id = str(uuid.uuid4())[:12]

        table = _get_dynamodb_resource().Table(_get_audit_table())

        item = {
            "PK": f"LOG#{date_key}",
            "SK": f"{iso_now}#{event_id}",
            "event_id": event_id,
            "event_type": event_type,
            "actor_type": "USER",
            "actor_id": actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "success": success,
            "timestamp": iso_now,
            "module": "PORTAL",
            # GSI keys for querying
            "GSI1PK": f"ACTOR#USER#{actor_id}",
            "GSI1SK": f"{iso_now}#{event_id}",
            "GSI2PK": f"ENTITY#{entity_type}#{entity_id}",
            "GSI2SK": f"{iso_now}#{event_id}",
            "GSI3PK": f"TYPE#{event_type}",
            "GSI3SK": f"{iso_now}#{event_id}",
        }

        if details:
            # Filter sensitive data
            safe_details = {
                k: v for k, v in details.items()
                if not any(s in k.lower() for s in ["password", "secret", "token", "key", "credential"])
            }
            if safe_details:
                item["details"] = safe_details

        if session_id:
            item["session_id"] = session_id
            item["GSI4PK"] = f"SESSION#{session_id}"
            item["GSI4SK"] = f"{iso_now}#{event_id}"

        table.put_item(Item=item)
        return True

    except Exception as e:
        # Fail silently - audit logging should never break the main flow
        print(f"[PortalAudit] Failed to log event: {e}")
        return False
