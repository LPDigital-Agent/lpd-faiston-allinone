# =============================================================================
# Counting Tools
# =============================================================================

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from google.adk.tools import tool
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "reconciliacao"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


class CountStatus:
    PENDING = "PENDING"
    COUNTED = "COUNTED"
    VERIFIED = "VERIFIED"
    DIVERGENT = "DIVERGENT"


class DivergenceType:
    POSITIVE = "POSITIVE"      # Fisico > Sistema (sobra)
    NEGATIVE = "NEGATIVE"      # Fisico < Sistema (falta)
    SERIAL_MISMATCH = "SERIAL_MISMATCH"
    LOCATION_MISMATCH = "LOCATION_MISMATCH"


@tool
@trace_tool_call("sga_submit_count")
async def submit_count_tool(
    campaign_id: str,
    part_number: str,
    location_id: str,
    counted_quantity: int,
    counted_serials: Optional[List[str]] = None,
    counted_by: str = "system",
    evidence_keys: Optional[List[str]] = None,
    notes: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit a count result for a campaign item.

    Args:
        campaign_id: Campaign ID
        part_number: Part number counted
        location_id: Location counted
        counted_quantity: Physical count
        counted_serials: Serial numbers found
        counted_by: User who counted
        evidence_keys: S3 keys for photos
        notes: Additional notes
    """
    audit.working(
        message=f"Registrando contagem: {part_number} @ {location_id}",
        session_id=session_id,
    )

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Get count item
        count_item = await db.get_count_item(campaign_id, part_number, location_id)

        if not count_item:
            return {
                "success": False,
                "error": f"Item de contagem nao encontrado: {part_number} @ {location_id}",
            }

        if count_item.get("status") not in [CountStatus.PENDING, CountStatus.COUNTED]:
            return {
                "success": False,
                "error": f"Item ja foi processado. Status: {count_item.get('status')}",
            }

        now = datetime.utcnow().isoformat() + "Z"

        # Check if campaign requires double count
        campaign = await db.get_campaign(campaign_id)
        require_double = campaign and campaign.get("require_double_count", False)

        # Determine new status
        system_qty = count_item.get("system_quantity", 0)
        is_divergent = counted_quantity != system_qty

        if require_double and not count_item.get("counted_by"):
            # First count, needs verification
            new_status = CountStatus.COUNTED
        elif require_double and count_item.get("counted_by") == counted_by:
            # Same person trying to verify - not allowed
            return {
                "success": False,
                "error": "Verificacao deve ser feita por pessoa diferente",
            }
        else:
            # Final count or no double-count required
            new_status = CountStatus.DIVERGENT if is_divergent else CountStatus.VERIFIED

        # Update count item
        updates = {
            "counted_quantity": counted_quantity,
            "counted_serials": counted_serials or [],
            "counted_by": counted_by,
            "counted_at": now,
            "status": new_status,
            "evidence_keys": evidence_keys or [],
            "notes": notes,
        }

        if new_status in [CountStatus.VERIFIED, CountStatus.DIVERGENT]:
            updates["verified_by"] = counted_by
            updates["verified_at"] = now

        await db.update_count_item(campaign_id, part_number, location_id, updates)

        # Update campaign counters
        await _update_campaign_counters(campaign_id)

        # If divergent, create divergence record
        if new_status == CountStatus.DIVERGENT:
            await _create_divergence_record(
                campaign_id=campaign_id,
                count_item=count_item,
                counted_quantity=counted_quantity,
                counted_serials=counted_serials or [],
            )

        audit.completed(
            message=f"Contagem registrada: {new_status}",
            session_id=session_id,
            details={
                "system_quantity": system_qty,
                "counted_quantity": counted_quantity,
                "is_divergent": is_divergent,
            },
        )

        return {
            "success": True,
            "campaign_id": campaign_id,
            "message": f"Contagem registrada. Status: {new_status}",
            "data": {
                "part_number": part_number,
                "location_id": location_id,
                "system_quantity": system_qty,
                "counted_quantity": counted_quantity,
                "status": new_status,
                "is_divergent": is_divergent,
            },
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[submit_count] Error: {e}", exc_info=True)
        audit.error(message="Erro ao registrar contagem", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}


async def _update_campaign_counters(campaign_id: str) -> None:
    """Update campaign progress counters."""
    try:
        from tools.db_client import DBClient
        db = DBClient()

        items = await db.get_campaign_items(campaign_id)

        counted = len([i for i in items if i.get("status") != CountStatus.PENDING])
        divergent = len([i for i in items if i.get("status") == CountStatus.DIVERGENT])

        await db.update_campaign(campaign_id, {
            "counted_items": counted,
            "divergent_items": divergent,
            "status": "IN_PROGRESS" if counted > 0 else "ACTIVE",
        })
    except ImportError:
        logger.warning("[_update_campaign_counters] DBClient not available")


async def _create_divergence_record(
    campaign_id: str,
    count_item: Dict[str, Any],
    counted_quantity: int,
    counted_serials: List[str],
) -> None:
    """Create a divergence record for analysis."""
    system_qty = count_item.get("system_quantity", 0)
    diff = counted_quantity - system_qty

    # Determine divergence type
    if diff > 0:
        div_type = DivergenceType.POSITIVE
    elif diff < 0:
        div_type = DivergenceType.NEGATIVE
    else:
        # Check for serial mismatches
        system_serials = set(count_item.get("system_serials", []))
        counted_set = set(counted_serials)
        if system_serials != counted_set:
            div_type = DivergenceType.SERIAL_MISMATCH
        else:
            return  # No actual divergence

    now = datetime.utcnow().isoformat() + "Z"
    div_id = f"DIV_{uuid.uuid4().hex[:12].upper()}"

    # Calculate percentage
    percentage = abs(diff) / system_qty if system_qty > 0 else 1.0

    div_data = {
        "divergence_id": div_id,
        "campaign_id": campaign_id,
        "part_number": count_item.get("part_number"),
        "location_id": count_item.get("location_id"),
        "project_id": count_item.get("project_id"),
        "divergence_type": div_type,
        "system_quantity": system_qty,
        "counted_quantity": counted_quantity,
        "divergence_quantity": abs(diff),
        "divergence_percentage": percentage,
        "system_serials": count_item.get("system_serials", []),
        "counted_serials": counted_serials,
        "status": "PENDING_ANALYSIS",
        "created_at": now,
    }

    try:
        from tools.db_client import DBClient
        db = DBClient()
        await db.put_divergence(div_data)
    except ImportError:
        logger.warning("[_create_divergence_record] DBClient not available")
