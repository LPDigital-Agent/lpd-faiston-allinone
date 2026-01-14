# =============================================================================
# Validate Origin Tool
# Traceability validation for reverse logistics
# =============================================================================

import logging
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


logger = logging.getLogger(__name__)


# =============================================================================
# Tool Implementation
# =============================================================================


async def validate_origin_tool(
    serial_number: str,
    expected_reference: Optional[str] = None,
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate traceability for a return by finding the original exit movement.

    Business Rules:
    1. Every return MUST have a reference to an exit movement
    2. Serial number must exist in the system
    3. Project must match the original movement (if specified)
    4. Equipment must currently be in "EM_CAMPO" or "CONSERTO" status

    Args:
        serial_number: Equipment serial number to validate
        expected_reference: Expected origin reference (chamado, NF, etc.)
        project_id: Project ID to validate against
        session_id: Session ID for audit trail

    Returns:
        Dict with validation result and origin movement details
    """
    from shared.audit_emitter import AgentAuditEmitter

    audit = AgentAuditEmitter(agent_id="reverse")

    audit.working(
        f"Validando rastreabilidade: {serial_number}",
        session_id=session_id,
    )

    try:
        if not serial_number:
            return {
                "success": False,
                "valid": False,
                "error": "Serial number é obrigatório",
            }

        # Look up equipment
        equipment = await _lookup_equipment(serial_number)

        if not equipment:
            audit.completed(
                f"Equipamento não encontrado: {serial_number}",
                session_id=session_id,
            )
            return {
                "success": True,
                "valid": False,
                "reason": "EQUIPMENT_NOT_FOUND",
                "message": f"Equipamento não cadastrado no sistema: {serial_number}",
            }

        # Check current status
        current_status = equipment.get("status", "")
        valid_statuses = ["EM_CAMPO", "CONSERTO", "DEMONSTRACAO", "LOCACAO", "EMPRESTIMO"]

        if current_status not in valid_statuses:
            audit.completed(
                f"Status inválido para retorno: {current_status}",
                session_id=session_id,
            )
            return {
                "success": True,
                "valid": False,
                "reason": "INVALID_STATUS",
                "message": f"Equipamento não está em campo. Status atual: {current_status}",
                "current_status": current_status,
                "valid_statuses": valid_statuses,
            }

        # Find original exit movement
        origin_movement = await _find_origin_movement(serial_number)

        if not origin_movement:
            audit.completed(
                f"Movimento de saída não encontrado: {serial_number}",
                session_id=session_id,
            )
            return {
                "success": True,
                "valid": False,
                "reason": "NO_EXIT_MOVEMENT",
                "message": "Não foi encontrado movimento de saída para este equipamento",
            }

        # Validate project if specified
        if project_id:
            origin_project = origin_movement.get("project_id")
            if origin_project and origin_project != project_id:
                audit.completed(
                    f"Projeto divergente: esperado {project_id}, encontrado {origin_project}",
                    session_id=session_id,
                )
                return {
                    "success": True,
                    "valid": False,
                    "reason": "PROJECT_MISMATCH",
                    "message": f"Projeto não corresponde ao movimento original",
                    "expected_project": project_id,
                    "actual_project": origin_project,
                }

        # Validate reference if specified
        if expected_reference:
            origin_ref = origin_movement.get("reference")
            if origin_ref and origin_ref != expected_reference:
                # Warning but still valid
                audit.working(
                    f"Referência diferente: esperado {expected_reference}, encontrado {origin_ref}",
                    session_id=session_id,
                )

        # Calculate time since exit
        exit_date = origin_movement.get("created_at")
        days_in_field = None
        if exit_date:
            try:
                exit_dt = datetime.fromisoformat(exit_date.replace("Z", "+00:00"))
                days_in_field = (datetime.now(exit_dt.tzinfo) - exit_dt).days
            except Exception:
                pass

        audit.completed(
            f"Rastreabilidade validada: {serial_number}",
            session_id=session_id,
            details={
                "origin_movement_id": origin_movement.get("movement_id"),
                "days_in_field": days_in_field,
            },
        )

        return {
            "success": True,
            "valid": True,
            "equipment": {
                "serial_number": serial_number,
                "part_number": equipment.get("part_number"),
                "description": equipment.get("description"),
                "owner": equipment.get("owner"),
                "current_status": current_status,
            },
            "origin_movement": {
                "movement_id": origin_movement.get("movement_id"),
                "type": origin_movement.get("type"),
                "reference": origin_movement.get("reference"),
                "project_id": origin_movement.get("project_id"),
                "destination": origin_movement.get("destination"),
                "created_at": origin_movement.get("created_at"),
            },
            "days_in_field": days_in_field,
            "message": "Rastreabilidade validada com sucesso",
        }

    except Exception as e:
        logger.error(f"[validate_origin] Error: {e}", exc_info=True)
        audit.error(
            f"Erro ao validar rastreabilidade: {serial_number}",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "valid": False,
            "error": str(e),
        }


async def _lookup_equipment(serial_number: str) -> Optional[Dict[str, Any]]:
    """
    Look up equipment by serial number.

    In production, queries PostgreSQL via MCP Gateway.
    """
    # Simulate equipment data
    return {
        "id": str(uuid.uuid4()),
        "serial_number": serial_number,
        "part_number": "PN-12345",
        "description": "Equipment Description",
        "owner": "FAISTON",
        "status": "EM_CAMPO",
    }


async def _find_origin_movement(serial_number: str) -> Optional[Dict[str, Any]]:
    """
    Find the original exit movement for an equipment.

    In production:
    SELECT * FROM movements
    WHERE serial_number = $1
      AND type IN ('EXIT', 'EXPEDITION', 'CONSERTO')
    ORDER BY created_at DESC
    LIMIT 1
    """
    # Simulate origin movement
    return {
        "movement_id": str(uuid.uuid4()),
        "type": "EXIT",
        "serial_number": serial_number,
        "reference": "CHAMADO-2024-001",
        "project_id": "PRJ-001",
        "destination": "Cliente XYZ",
        "created_at": "2024-01-15T10:30:00Z",
    }
