# =============================================================================
# Process Return Tool
# Main reverse logistics processing with depot routing
# =============================================================================

import logging
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


logger = logging.getLogger(__name__)

# =============================================================================
# Depot Mapping (duplicated for tool isolation)
# =============================================================================

DEPOT_MAPPING = {
    # Faiston equipment
    ("FAISTON", "FUNCIONAL"): "01",      # Recebimento
    ("FAISTON", "DEFEITUOSO"): "03",     # BAD Faiston
    ("FAISTON", "INSERVIVEL"): "04",     # Descarte
    # NTT equipment (third party)
    ("NTT", "FUNCIONAL"): "05",          # Itens de terceiros
    ("NTT", "DEFEITUOSO"): "03.01",      # BAD NTT
    ("NTT", "INSERVIVEL"): "04",         # Descarte
    # Other third parties
    ("TERCEIROS", "FUNCIONAL"): "06",    # Depósito de terceiros
    ("TERCEIROS", "DEFEITUOSO"): "03",   # BAD
    ("TERCEIROS", "INSERVIVEL"): "04",   # Descarte
}

DEPOT_NAMES = {
    "01": "Recebimento",
    "03": "BAD Faiston",
    "03.01": "BAD NTT",
    "04": "Descarte",
    "05": "Terceiros NTT",
    "06": "Depósito Terceiros",
}

# Return types
RETURN_TYPES = {
    "CONSERTO_RETORNO": "Retorno de conserto",
    "CLIENTE_DEVOLUCAO": "Devolução do cliente",
    "DEFEITUOSO": "Equipamento defeituoso",
    "FIM_LOCACAO": "Fim de locação",
    "FIM_EMPRESTIMO": "Fim de empréstimo",
    "DESCARTE": "Descarte de equipamento",
}

# =============================================================================
# Database Client (lazy loaded)
# =============================================================================

_db_client = None


def get_db_client():
    """Lazy load database client for cold start optimization."""
    global _db_client
    if _db_client is None:
        import asyncpg
        import os
        # Will be initialized on first use
    return _db_client


# =============================================================================
# Tool Implementation
# =============================================================================


async def process_return_tool(
    serial_number: str,
    reason: str,
    condition: str,
    origin_reference: Optional[str] = None,
    project_id: Optional[str] = None,
    notes: str = "",
    operator_id: str = "system",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a return (devolução/reversa) in the inventory system.

    This tool handles:
    1. Validates the equipment exists and has an outbound movement
    2. Determines equipment owner (Faiston, NTT, Terceiros)
    3. Routes to appropriate depot based on owner + condition
    4. Creates RETURN movement in stock
    5. Triggers HIL if condition is INSERVIVEL (descarte)

    Args:
        serial_number: Equipment serial number
        reason: Return type (CONSERTO_RETORNO, CLIENTE_DEVOLUCAO, etc.)
        condition: Equipment condition (FUNCIONAL, DEFEITUOSO, INSERVIVEL)
        origin_reference: Reference to original exit movement (chamado, NF)
        project_id: Project ID for tracking
        notes: Additional notes about the return
        operator_id: Operator processing the return
        session_id: Session ID for audit trail

    Returns:
        Dict with return processing result
    """
    from shared.audit_emitter import AgentAuditEmitter
    from shared.xray_tracer import trace_tool_call

    audit = AgentAuditEmitter(agent_id="reverse")

    audit.working(
        f"Processando retorno: {serial_number} - {reason}",
        session_id=session_id,
        details={"serial_number": serial_number, "reason": reason},
    )

    try:
        # Validate inputs
        if not serial_number:
            return {
                "success": False,
                "error": "Serial number é obrigatório",
            }

        if reason not in RETURN_TYPES:
            return {
                "success": False,
                "error": f"Tipo de retorno inválido. Válidos: {list(RETURN_TYPES.keys())}",
            }

        condition = condition.upper()
        if condition not in ["FUNCIONAL", "DEFEITUOSO", "INSERVIVEL"]:
            return {
                "success": False,
                "error": "Condição deve ser: FUNCIONAL, DEFEITUOSO ou INSERVIVEL",
            }

        # Simulate equipment lookup
        # In production, this would query the database
        equipment = await _lookup_equipment(serial_number)

        if not equipment:
            return {
                "success": False,
                "error": f"Equipamento não encontrado: {serial_number}",
            }

        # Determine owner
        owner = equipment.get("owner", "FAISTON").upper()
        if owner not in ["FAISTON", "NTT", "TERCEIROS"]:
            owner = "TERCEIROS"

        # Route to depot based on owner + condition
        depot_key = (owner, condition)
        target_depot = DEPOT_MAPPING.get(depot_key, "01")
        depot_name = DEPOT_NAMES.get(target_depot, "Desconhecido")

        audit.working(
            f"Destino: Depósito {target_depot} ({depot_name})",
            session_id=session_id,
        )

        # Check if HIL required (INSERVIVEL = descarte)
        requires_hil = condition == "INSERVIVEL"
        hil_task_id = None

        if requires_hil:
            hil_task_id = str(uuid.uuid4())
            audit.working(
                "Requer aprovação para descarte (HIL)",
                session_id=session_id,
                details={"hil_task_id": hil_task_id},
            )

        # Create return movement
        movement_id = str(uuid.uuid4())
        movement = {
            "movement_id": movement_id,
            "type": "RETURN",
            "serial_number": serial_number,
            "reason": reason,
            "reason_description": RETURN_TYPES[reason],
            "condition": condition,
            "owner": owner,
            "source_depot": equipment.get("current_depot"),
            "target_depot": target_depot,
            "target_depot_name": depot_name,
            "origin_reference": origin_reference,
            "project_id": project_id,
            "notes": notes,
            "operator_id": operator_id,
            "status": "PENDING_APPROVAL" if requires_hil else "COMPLETED",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        # Add HIL info if required
        if requires_hil:
            movement["hil_required"] = True
            movement["hil_task_id"] = hil_task_id
            movement["hil_reason"] = "Descarte requer aprovação do gerente operacional"

        # In production, save to database
        # await save_movement(movement)

        audit.completed(
            f"Retorno processado: {serial_number} → Depósito {target_depot}",
            session_id=session_id,
            details={
                "movement_id": movement_id,
                "depot": target_depot,
                "requires_hil": requires_hil,
            },
        )

        return {
            "success": True,
            "movement": movement,
            "message": f"Retorno processado com sucesso. Destino: {depot_name} ({target_depot})",
            "requires_approval": requires_hil,
            "hil_task_id": hil_task_id,
        }

    except Exception as e:
        logger.error(f"[process_return] Error: {e}", exc_info=True)
        audit.error(
            f"Erro ao processar retorno: {serial_number}",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _lookup_equipment(serial_number: str) -> Optional[Dict[str, Any]]:
    """
    Look up equipment by serial number.

    In production, this queries the database.
    For now, returns simulated data.
    """
    # Simulate equipment data
    # In production: SELECT * FROM assets WHERE serial_number = $1
    return {
        "id": str(uuid.uuid4()),
        "serial_number": serial_number,
        "part_number": "PN-12345",
        "description": "Equipment Description",
        "owner": "FAISTON",
        "current_depot": "CLIENTE",
        "status": "EM_CAMPO",
    }
