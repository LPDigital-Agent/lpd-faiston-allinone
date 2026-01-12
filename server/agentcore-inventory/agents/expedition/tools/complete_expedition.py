# =============================================================================
# Complete Expedition Tools
# =============================================================================

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "expedition"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


def generate_movement_id() -> str:
    """Generate movement ID."""
    return f"MV_{uuid.uuid4().hex[:12].upper()}"


@trace_tool_call("sga_complete_expedition")
async def complete_expedition_tool(
    expedition_id: str,
    nf_number: str,
    nf_key: str,
    carrier: str,
    tracking_code: Optional[str] = None,
    operator_id: str = "system",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Complete the expedition after NF emission.

    Creates EXIT movements and updates stock.

    Args:
        expedition_id: Expedition ID
        nf_number: NF number
        nf_key: NF access key (44 digits)
        carrier: Carrier/transportadora name
        tracking_code: Optional tracking number
        operator_id: User completing
    """
    audit.working(
        message=f"Completando expedicao: {expedition_id}",
        session_id=session_id,
    )

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Get expedition record
        expedition = await db.get_expedition(expedition_id)

        if not expedition:
            return {
                "success": False,
                "error": f"Expedicao nao encontrada: {expedition_id}",
            }

        if expedition.get("status") not in ["SEPARATED", "PENDING_SEPARATION"]:
            return {
                "success": False,
                "error": f"Status invalido para conclusao: {expedition.get('status')}",
            }

        items = expedition.get("items_confirmed") or expedition.get("items", [])
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Create EXIT movements for each item
        movements = []
        for item in items:
            movement_id = generate_movement_id()

            movement_data = {
                "movement_id": movement_id,
                "movement_type": "EXIT",
                "pn_id": item.get("pn_id", ""),
                "serial_number": item.get("serial", ""),
                "quantity": -item.get("quantity", 1),  # Negative for exit
                "source_location_id": item.get("location_id", "01"),
                "destination": expedition.get("destination_client", ""),
                "project_id": expedition.get("project_id", ""),
                "expedition_id": expedition_id,
                "nf_number": nf_number,
                "nf_key": nf_key,
                "carrier": carrier,
                "tracking_code": tracking_code or "",
                "operator_id": operator_id,
                "status": "COMPLETED",
                "created_at": timestamp,
            }

            await db.put_movement(movement_data)
            movements.append(movement_id)

            # Update balance
            await db.update_balance(
                pn_id=item.get("pn_id", ""),
                location_id=item.get("location_id", "01"),
                delta=-item.get("quantity", 1),
            )

            # Release reservation
            await db.release_reservation(
                expedition_id=expedition_id,
                pn_id=item.get("pn_id", ""),
            )

        # Update expedition status
        updates = {
            "status": "COMPLETED",
            "completed_at": timestamp,
            "completed_by": operator_id,
            "nf_number": nf_number,
            "nf_key": nf_key,
            "carrier": carrier,
            "tracking_code": tracking_code or "",
            "movements": movements,
            "updated_at": timestamp,
        }

        await db.update_expedition(expedition_id, updates)

        audit.completed(
            message=f"Expedicao concluida: NF {nf_number}",
            session_id=session_id,
            details={
                "movements_count": len(movements),
                "nf_number": nf_number,
                "tracking_code": tracking_code,
            },
        )

        return {
            "success": True,
            "expedition_id": expedition_id,
            "status": "COMPLETED",
            "movements_created": movements,
            "nf_number": nf_number,
            "nf_key": nf_key,
            "carrier": carrier,
            "tracking_code": tracking_code,
            "message": f"Expedicao concluida com sucesso. NF {nf_number}.",
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[complete_expedition] Error: {e}", exc_info=True)
        audit.error(message="Erro ao completar expedicao", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
