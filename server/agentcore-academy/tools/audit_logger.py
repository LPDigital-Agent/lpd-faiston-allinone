# =============================================================================
# Audit Logger for Academy Agents
# =============================================================================
# Lightweight audit logging wrapper that logs to the shared SGA audit table.
# Uses lazy imports to avoid cold start issues.
#
# Event types use ACADEMY_* prefix to distinguish from SGA events.
# =============================================================================

from typing import Dict, Any, Optional
import os

# Lazy imports - boto3 imported only when needed
_dynamodb_resource = None


def _get_dynamodb_resource():
    """
    Get DynamoDB resource with lazy initialization.

    Returns:
        boto3 DynamoDB resource
    """
    global _dynamodb_resource
    if _dynamodb_resource is None:
        import boto3
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


def _get_audit_table() -> str:
    """Get audit log table name from environment."""
    # Uses the same audit table as SGA - shared audit log
    return os.environ.get("AUDIT_LOG_TABLE", "faiston-one-sga-audit-log-prod")


def log_academy_event(
    event_type: str,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    actor_type: str = "USER",
) -> bool:
    """
    Log an Academy audit event to DynamoDB.

    This is a lightweight wrapper that logs to the shared SGA audit table.
    All event types should use the ACADEMY_* prefix.

    Args:
        event_type: Type of event (ACADEMY_NEXO_CHAT, ACADEMY_FLASHCARD_GENERATE, etc.)
        actor_id: User identifier (user_id)
        entity_type: Entity type affected (CONVERSATION, FLASHCARD, MINDMAP, etc.)
        entity_id: Entity identifier (session_id, episode_id, training_id)
        action: Action performed (nexo_chat, generate_flashcards, etc.)
        details: Additional safe-to-log details (prompt_length, count, etc.)
        session_id: Optional session identifier for grouping related events
        actor_type: Actor type (USER, AGENT, SYSTEM) - defaults to USER

    Returns:
        True if successful, False otherwise

    Example:
        log_academy_event(
            event_type="ACADEMY_NEXO_CHAT",
            actor_id=user_id,
            entity_type="CONVERSATION",
            entity_id=session_id,
            action="nexo_chat",
            details={"prompt_length": len(prompt)},
            session_id=session_id
        )
    """
    try:
        from datetime import datetime
        import uuid

        # Get table
        table = _get_dynamodb_resource().Table(_get_audit_table())

        # Generate event metadata
        now = datetime.utcnow()
        iso_now = now.isoformat() + "Z"
        date_key = now.strftime("%Y-%m-%d")
        event_id = str(uuid.uuid4())[:12]

        # Build audit item
        item = {
            "PK": f"LOG#{date_key}",
            "SK": f"{iso_now}#{event_id}",
            "event_id": event_id,
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "timestamp": iso_now,
            "created_at": iso_now,
            "updated_at": iso_now,
            # GSI keys for querying
            "GSI1PK": f"ACTOR#{actor_type}#{actor_id}",
            "GSI1SK": f"{iso_now}#{event_id}",
            "GSI2PK": f"ENTITY#{entity_type}#{entity_id}",
            "GSI2SK": f"{iso_now}#{event_id}",
            "GSI3PK": f"TYPE#{event_type}",
            "GSI3SK": f"{iso_now}#{event_id}",
        }

        # Add details (filter sensitive data)
        if details:
            safe_details = {
                k: v for k, v in details.items()
                if not any(s in k.lower() for s in ["password", "secret", "token", "key", "transcription"])
            }
            if safe_details:
                item["details"] = safe_details

        # Add session_id for grouping related events
        if session_id:
            item["session_id"] = session_id
            item["GSI4PK"] = f"SESSION#{session_id}"
            item["GSI4SK"] = f"{iso_now}#{event_id}"

        # Write to DynamoDB
        table.put_item(Item=item)
        return True

    except Exception as e:
        # Log error but don't fail the request
        print(f"[Academy Audit] Failed to log event: {e}")
        return False


def log_academy_error(
    event_type: str,
    actor_id: str,
    action: str,
    error: str,
    session_id: Optional[str] = None,
) -> bool:
    """
    Log an Academy error event.

    Convenience wrapper for logging failures/errors.

    Args:
        event_type: Type of event (e.g., ACADEMY_NEXO_CHAT)
        actor_id: User identifier
        action: Action that failed
        error: Error message
        session_id: Optional session identifier

    Returns:
        True if successful
    """
    return log_academy_event(
        event_type=f"{event_type}_ERROR",
        actor_id=actor_id,
        entity_type="ERROR",
        entity_id=action,
        action=action,
        details={"error": str(error)[:500]},  # Truncate error messages
        session_id=session_id,
    )
