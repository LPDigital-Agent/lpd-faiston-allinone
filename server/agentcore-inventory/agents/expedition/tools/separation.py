# =============================================================================
# Separation Confirmation Tools
# =============================================================================

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from google.adk.tools import tool
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "expedition"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@tool
@trace_tool_call("sga_confirm_separation")
async def confirm_separation_tool(
    expedition_id: str,
    items_confirmed: List[Dict[str, Any]],
    package_info: Dict[str, Any],
    operator_id: str = "system",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Confirm physical separation and packaging.

    Args:
        expedition_id: Expedition ID
        items_confirmed: List of confirmed items with serials
        package_info: Packaging details (weight, dimensions)
        operator_id: User confirming separation
    """
    audit.working(
        message=f"Confirmando separacao: {expedition_id}",
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

        if expedition.get("status") != "PENDING_SEPARATION":
            return {
                "success": False,
                "error": f"Status invalido para separacao: {expedition.get('status')}",
            }

        now = datetime.utcnow().isoformat() + "Z"

        # Update expedition status
        updates = {
            "status": "SEPARATED",
            "separation_confirmed_at": now,
            "separation_confirmed_by": operator_id,
            "package_info": package_info,
            "items_confirmed": items_confirmed,
            "updated_at": now,
        }

        await db.update_expedition(expedition_id, updates)

        audit.completed(
            message=f"Separacao confirmada: {expedition_id}",
            session_id=session_id,
            details={"items_count": len(items_confirmed)},
        )

        return {
            "success": True,
            "expedition_id": expedition_id,
            "status": "SEPARATED",
            "message": "Separacao confirmada. Pronto para emissao de NF.",
            "package_info": package_info,
            "next_steps": [
                "1. Emitir NF no SAP",
                "2. Transmitir para SEFAZ",
                "3. Imprimir DANFE",
                "4. Despachar com transportadora",
            ],
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[confirm_separation] Error: {e}", exc_info=True)
        audit.error(message="Erro ao confirmar separacao", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
