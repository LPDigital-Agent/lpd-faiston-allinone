# =============================================================================
# Adjustment Proposal Tools
# =============================================================================

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "reconciliacao"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@trace_tool_call("sga_propose_adjustment")
async def propose_adjustment_tool(
    campaign_id: str,
    part_number: str,
    location_id: str,
    proposed_by: str = "system",
    adjustment_reason: str = "",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Propose an inventory adjustment based on counting.

    ALWAYS creates HIL task - adjustments are NEVER automatic.
    """
    audit.working(
        message=f"Propondo ajuste: {part_number} @ {location_id}",
        session_id=session_id,
    )

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Get count item
        count_item = await db.get_count_item(campaign_id, part_number, location_id)

        if not count_item:
            return {"success": False, "error": "Item de contagem nao encontrado"}

        if count_item.get("status") != "DIVERGENT":
            return {"success": False, "error": "Item nao possui divergencia"}

        system_qty = count_item.get("system_quantity", 0)
        counted_qty = count_item.get("counted_quantity", 0)
        adjustment_qty = counted_qty - system_qty

        now = datetime.utcnow().isoformat() + "Z"
        movement_id = f"ADJ_{uuid.uuid4().hex[:12].upper()}"

        # Create pending adjustment movement
        movement_data = {
            "movement_id": movement_id,
            "movement_type": "ADJUSTMENT",
            "part_number": part_number,
            "quantity": adjustment_qty,
            "location_id": location_id,
            "project_id": count_item.get("project_id", ""),
            "campaign_id": campaign_id,
            "status": "PENDING_APPROVAL",
            "adjustment_reason": adjustment_reason,
            "system_quantity_before": system_qty,
            "counted_quantity": counted_qty,
            "proposed_by": proposed_by,
            "created_at": now,
        }

        await db.put_movement(movement_data)

        # Create HIL task (MANDATORY for adjustments)
        hil_task_id = None
        try:
            from tools.hil_workflow import HILWorkflowManager
            hil_manager = HILWorkflowManager()

            adj_type = "ENTRADA" if adjustment_qty > 0 else "BAIXA"
            hil_task = await hil_manager.create_task(
                task_type="APPROVAL_ADJUSTMENT",
                title=f"Aprovar ajuste de inventario: {part_number}",
                description=_format_adjustment_message(
                    part_number=part_number,
                    location_id=location_id,
                    system_qty=system_qty,
                    counted_qty=counted_qty,
                    adjustment_qty=adjustment_qty,
                    reason=adjustment_reason,
                ),
                entity_type="MOVEMENT",
                entity_id=movement_id,
                requested_by=proposed_by,
                payload=movement_data,
                priority="HIGH",
            )
            hil_task_id = hil_task.get("task_id")

            # Update movement with task ID
            await db.update_movement(movement_id, {"hil_task_id": hil_task_id})

        except ImportError:
            logger.warning("[propose_adjustment] HILWorkflowManager not available")

        adj_type = "ENTRADA" if adjustment_qty > 0 else "BAIXA"

        audit.completed(
            message=f"Proposta de ajuste criada: {adj_type} de {abs(adjustment_qty)} unidades",
            session_id=session_id,
            details={
                "movement_id": movement_id,
                "hil_task_id": hil_task_id,
                "adjustment_quantity": adjustment_qty,
            },
        )

        return {
            "success": True,
            "campaign_id": campaign_id,
            "message": f"Proposta de ajuste criada. {adj_type} de {abs(adjustment_qty)} unidades.",
            "data": {
                "movement_id": movement_id,
                "hil_task_id": hil_task_id,
                "adjustment_type": adj_type,
                "adjustment_quantity": adjustment_qty,
                "requires_approval": True,
            },
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[propose_adjustment] Error: {e}", exc_info=True)
        audit.error(message="Erro ao propor ajuste", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}


def _format_adjustment_message(
    part_number: str,
    location_id: str,
    system_qty: int,
    counted_qty: int,
    adjustment_qty: int,
    reason: str,
) -> str:
    """Format HIL message for adjustment approval."""
    adj_type = "ENTRADA" if adjustment_qty > 0 else "BAIXA"

    return f"""
## Solicitacao de Ajuste de Inventario

### Resumo
Ajuste de **{adj_type}** proposto com base em contagem fisica.

### Detalhes
| Campo | Valor |
|-------|-------|
| Part Number | {part_number} |
| Local | {location_id} |
| Quantidade Sistema | {system_qty} |
| Quantidade Contada | {counted_qty} |
| **Ajuste Proposto** | **{adjustment_qty:+d}** |

### Motivo
{reason or "Divergencia identificada em campanha de inventario"}

### AVISO
Ajustes de inventario afetam diretamente o saldo contabil.
Certifique-se de que a contagem foi verificada antes de aprovar.

### Acoes Disponiveis
- **Aprovar**: Executar o ajuste conforme proposto
- **Rejeitar**: Cancelar o ajuste e manter saldo atual
- **Modificar**: Ajustar a quantidade antes de aprovar
"""
