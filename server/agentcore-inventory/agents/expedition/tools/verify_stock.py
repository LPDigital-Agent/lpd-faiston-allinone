# =============================================================================
# Verify Stock Tools
# =============================================================================

import logging
from typing import Dict, Any, Optional

from google.adk.tools import tool
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "expedition"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


async def verify_stock_item(
    pn_id: str,
    serial: Optional[str],
    quantity: int,
) -> Dict[str, Any]:
    """
    Verify stock availability for a single item.

    Internal helper function used by process_expedition.
    """
    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Get part number
        pn = await db.get_part_number(pn_id)

        if not pn:
            return {
                "available": False,
                "reason": f"Part number nao encontrado: {pn_id}",
            }

        # For serialized items, check specific asset
        if pn.get("is_serialized") and serial:
            asset = await db.get_asset_by_serial(serial)

            if not asset:
                return {
                    "available": False,
                    "pn": pn,
                    "reason": f"Serial nao encontrado: {serial}",
                }

            # Check if available (not reserved, not in transit)
            if asset.get("status") in ["RESERVED", "IN_TRANSIT", "MAINTENANCE"]:
                return {
                    "available": False,
                    "pn": pn,
                    "asset": asset,
                    "reason": f"Equipamento com status: {asset.get('status')}",
                }

            return {
                "available": True,
                "pn": pn,
                "asset": asset,
                "location_id": asset.get("location_id", "01"),
            }

        # For non-serialized, check balance
        else:
            balance = await db.get_balance(pn_id, "01")  # Default depot

            available_qty = (balance.get("quantity", 0) -
                           balance.get("reserved_quantity", 0))

            if available_qty < quantity:
                return {
                    "available": False,
                    "pn": pn,
                    "reason": f"Quantidade insuficiente. Disponivel: {available_qty}",
                }

            return {
                "available": True,
                "pn": pn,
                "location_id": "01",
                "available_quantity": available_qty,
            }

    except ImportError:
        logger.warning("[verify_stock_item] DBClient not available")
        # Return mock data for testing
        return {
            "available": True,
            "pn": {"pn_id": pn_id, "part_number": pn_id},
            "location_id": "01",
        }
    except Exception as e:
        logger.error(f"[verify_stock_item] Error: {e}", exc_info=True)
        return {
            "available": False,
            "reason": str(e),
        }


@tool
@trace_tool_call("sga_verify_stock")
async def verify_stock_tool(
    pn_id: str,
    serial: Optional[str] = None,
    quantity: int = 1,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify stock availability for an item.

    Args:
        pn_id: Part number ID
        serial: Optional serial number for serialized items
        quantity: Quantity needed
    """
    audit.working(
        message=f"Verificando estoque: {pn_id} (serial: {serial or 'N/A'})",
        session_id=session_id,
    )

    result = await verify_stock_item(pn_id, serial, quantity)

    if result.get("available"):
        audit.completed(
            message=f"Estoque disponivel: {pn_id}",
            session_id=session_id,
        )
    else:
        audit.completed(
            message=f"Estoque indisponivel: {result.get('reason')}",
            session_id=session_id,
        )

    return {
        "success": True,
        **result,
    }
