# =============================================================================
# Process Expedition Tools
# =============================================================================

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "expedition"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


def generate_expedition_id() -> str:
    """Generate expedition ID."""
    return f"EXP_{uuid.uuid4().hex[:12].upper()}"


@trace_tool_call("sga_process_expedition")
async def process_expedition_tool(
    chamado_id: str,
    project_id: str,
    items: List[Dict[str, Any]],
    destination_client: str,
    destination_address: str,
    urgency: str = "NORMAL",
    nature: str = "USO_CONSUMO",
    notes: str = "",
    operator_id: str = "system",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process an expedition request from a chamado.

    Args:
        chamado_id: Ticket/chamado ID
        project_id: Associated project
        items: List of items to ship [{pn_id, serial, quantity}]
        destination_client: Client name/CNPJ
        destination_address: Delivery address
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
        nature: Nature of operation for SAP
        notes: Additional notes
        operator_id: User processing the expedition
    """
    audit.working(
        message=f"Processando expedicao: chamado {chamado_id}",
        session_id=session_id,
    )

    try:
        from .verify_stock import verify_stock_item
        from .sap_export import generate_item_sap_data

        # Validate project
        try:
            from tools.db_client import DBClient
            db = DBClient()
            project = await db.get_project(project_id)
            if not project:
                return {
                    "success": False,
                    "error": f"Projeto nao encontrado: {project_id}",
                }
        except ImportError:
            logger.warning("[process_expedition] DBClient not available")
            project = {"project_id": project_id}

        # Generate expedition ID
        expedition_id = generate_expedition_id()
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Process each item
        verified_items = []
        unavailable_items = []
        sap_data_list = []

        for item in items:
            pn_id = item.get("pn_id", "")
            serial = item.get("serial", "")
            quantity = item.get("quantity", 1)

            # Verify stock availability
            verification = await verify_stock_item(pn_id, serial, quantity)

            if verification.get("available"):
                verified_items.append({
                    **item,
                    "pn": verification.get("pn"),
                    "asset": verification.get("asset"),
                    "location_id": verification.get("location_id"),
                })

                # Generate SAP data for this item
                sap_data = generate_item_sap_data(
                    pn=verification.get("pn", {}),
                    serial=serial,
                    quantity=quantity,
                    location_id=verification.get("location_id", "01"),
                    destination_client=destination_client,
                    nature=nature,
                    project_id=project_id,
                    chamado_id=chamado_id,
                )
                sap_data_list.append(sap_data)
            else:
                unavailable_items.append({
                    **item,
                    "reason": verification.get("reason", "Nao disponivel"),
                })

        # Create expedition record
        expedition_data = {
            "expedition_id": expedition_id,
            "chamado_id": chamado_id,
            "project_id": project_id,
            "items": verified_items,
            "unavailable_items": unavailable_items,
            "destination_client": destination_client,
            "destination_address": destination_address,
            "urgency": urgency,
            "nature": nature,
            "notes": notes,
            "status": "PENDING_SEPARATION" if verified_items else "FAILED",
            "sap_data": sap_data_list,
            "created_by": operator_id,
            "created_at": timestamp,
        }

        # Store expedition
        try:
            from tools.db_client import DBClient
            db = DBClient()
            await db.put_expedition(expedition_data)

            # Create reservations for verified items
            for v_item in verified_items:
                await db.create_reservation(
                    expedition_id=expedition_id,
                    pn_id=v_item["pn_id"],
                    serial=v_item.get("serial"),
                    quantity=v_item.get("quantity", 1),
                    location_id=v_item.get("location_id", "01"),
                    operator_id=operator_id,
                )
        except ImportError:
            logger.warning("[process_expedition] DBClient not available")

        audit.completed(
            message=f"Expedicao criada: {expedition_id} ({len(verified_items)} itens)",
            session_id=session_id,
            details={
                "expedition_id": expedition_id,
                "verified_items": len(verified_items),
                "unavailable_items": len(unavailable_items),
            },
        )

        return {
            "success": True,
            "expedition_id": expedition_id,
            "chamado_id": chamado_id,
            "project_id": project_id,
            "verified_items": verified_items,
            "unavailable_items": unavailable_items,
            "sap_data": sap_data_list,
            "status": expedition_data["status"],
            "next_steps": [
                "1. Separar itens fisicamente",
                "2. Embalar equipamento",
                "3. Copiar dados SAP para NF",
                "4. Confirmar expedicao no sistema",
            ],
        }

    except Exception as e:
        logger.error(f"[process_expedition] Error: {e}", exc_info=True)
        audit.error(message="Erro ao processar expedicao", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}


@trace_tool_call("sga_get_expedition")
async def get_expedition_tool(
    expedition_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get expedition details by ID."""
    try:
        from tools.db_client import DBClient
        db = DBClient()
        expedition = await db.get_expedition(expedition_id)

        if not expedition:
            return {"success": False, "error": "Expedicao nao encontrada"}

        return {"success": True, "expedition": expedition}

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[get_expedition] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
