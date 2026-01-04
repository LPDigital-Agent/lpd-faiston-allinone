# =============================================================================
# Shared Utilities for Faiston SGA Inventory Agents
# =============================================================================
# Common helpers used across all inventory management agents.
#
# Module: Gestao de Ativos -> Gestao de Estoque
# All agents use Gemini 3.0 Pro exclusively (per CLAUDE.md mandate).
#
# API Key Note:
# GOOGLE_API_KEY is passed via --env at deploy time (not runtime SSM lookup).
# This follows the AWS official example pattern.
# =============================================================================

import json
import re
from typing import Dict, Any, Optional
from datetime import datetime
import os

# =============================================================================
# Constants
# =============================================================================

# App name for Google ADK sessions
APP_NAME = "faiston-sga-inventory"

# Agent version for tracking
AGENT_VERSION = "2026.01.04.v1"

# Model ID - All agents use Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
MODEL_GEMINI = "gemini-3-pro-preview"

# Environment variables
INVENTORY_TABLE = os.environ.get("INVENTORY_TABLE", "faiston-one-sga-inventory-prod")
HIL_TASKS_TABLE = os.environ.get("HIL_TASKS_TABLE", "faiston-one-sga-hil-tasks-prod")
AUDIT_LOG_TABLE = os.environ.get("AUDIT_LOG_TABLE", "faiston-one-sga-audit-log-prod")
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET", "faiston-one-sga-documents-prod")

# =============================================================================
# Entity Prefixes (Single-Table Design)
# =============================================================================

class EntityPrefix:
    """DynamoDB entity type prefixes for single-table design."""
    PART_NUMBER = "PN#"
    ASSET = "ASSET#"
    LOCATION = "LOC#"
    BALANCE = "BALANCE#"
    MOVEMENT = "MOVE#"
    RESERVATION = "RESERVE#"
    TASK = "TASK#"
    DIVERGENCE = "DIV#"
    DOCUMENT = "DOC#"
    PROJECT = "PROJ#"


# =============================================================================
# Movement Types
# =============================================================================

class MovementType:
    """Inventory movement types."""
    ENTRY = "ENTRY"           # Entrada (Internalizacao)
    EXIT = "EXIT"             # Saida (Expedicao)
    TRANSFER = "TRANSFER"     # Transferencia
    ADJUSTMENT = "ADJUSTMENT" # Ajuste (HIL required)
    RESERVATION = "RESERVATION"  # Reserva
    UNRESERVATION = "UNRESERVATION"  # Desreserva
    RETURN = "RETURN"         # Reversa
    DISCARD = "DISCARD"       # Descarte (HIL required)
    LOSS = "LOSS"             # Extravio (HIL required)


# =============================================================================
# HIL Task Types
# =============================================================================

class HILTaskType:
    """Human-in-the-Loop task types."""
    APPROVAL_NEW_PN = "APPROVAL_NEW_PN"
    APPROVAL_ENTRY = "APPROVAL_ENTRY"
    APPROVAL_ADJUSTMENT = "APPROVAL_ADJUSTMENT"
    APPROVAL_DISCARD = "APPROVAL_DISCARD"
    APPROVAL_TRANSFER = "APPROVAL_TRANSFER"
    REVIEW_ENTRY = "REVIEW_ENTRY"
    ESCALATION = "ESCALATION"


class HILTaskStatus:
    """HIL task status values."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# =============================================================================
# Confidence Scoring
# =============================================================================

class RiskLevel:
    """Risk level indicators for AI decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# JSON Parsing Utilities
# =============================================================================


def extract_json(response: str) -> str:
    """
    Extract JSON from a response that may contain markdown code blocks.

    Args:
        response: Raw response text from LLM

    Returns:
        Extracted JSON string
    """
    # Try to find JSON in markdown code block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if json_match:
        return json_match.group(1).strip()

    # Try to find raw JSON object or array
    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response)
    if json_match:
        return json_match.group(1).strip()

    # Return as-is if no JSON found
    return response.strip()


def parse_json_safe(response: str) -> Dict[str, Any]:
    """
    Safely parse JSON from response with fallback.

    Args:
        response: Raw response text from LLM

    Returns:
        Parsed JSON dict or error dict
    """
    try:
        json_str = extract_json(response)
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON: {e}", "raw_response": response}


# =============================================================================
# Date/Time Utilities
# =============================================================================


def now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"


def now_yyyymm() -> str:
    """Return current UTC date in YYYY-MM format for GSI5 partitioning."""
    return datetime.utcnow().strftime("%Y-%m")


def now_yyyymmdd() -> str:
    """Return current UTC date in YYYY-MM-DD format for audit log partitioning."""
    return datetime.utcnow().strftime("%Y-%m-%d")


# =============================================================================
# ID Generation
# =============================================================================


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID with optional prefix.

    Args:
        prefix: Optional prefix (e.g., "MOVE", "TASK")

    Returns:
        Unique ID string
    """
    import uuid
    unique = str(uuid.uuid4())[:12]
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    if prefix:
        return f"{prefix}-{timestamp}-{unique}"
    return f"{timestamp}-{unique}"


# =============================================================================
# Logging Utilities (Secure - No PII)
# =============================================================================


def log_agent_action(
    agent_name: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: str = "started",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log agent action for observability.

    SECURITY: Never log PII, credentials, or sensitive data.
    Only log action metadata for debugging and audit.

    Args:
        agent_name: Name of the agent performing the action
        action: Action being performed
        entity_type: Type of entity being operated on
        entity_id: ID of entity (safe to log, not PII)
        status: Action status (started, completed, failed)
        details: Additional safe-to-log details
    """
    log_entry = {
        "timestamp": now_iso(),
        "agent": agent_name,
        "action": action,
        "status": status,
    }
    if entity_type:
        log_entry["entity_type"] = entity_type
    if entity_id:
        log_entry["entity_id"] = entity_id
    if details:
        # Filter out any potentially sensitive keys
        safe_keys = {"count", "batch_size", "duration_ms", "confidence", "risk_level"}
        safe_details = {k: v for k, v in details.items() if k in safe_keys}
        if safe_details:
            log_entry["details"] = safe_details

    print(json.dumps(log_entry))
