# =============================================================================
# Evaluate Condition Tool
# AI-assisted equipment condition evaluation
# =============================================================================

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import json


logger = logging.getLogger(__name__)

# =============================================================================
# Condition Criteria
# =============================================================================

CONDITION_CRITERIA = {
    "FUNCIONAL": {
        "description": "Equipamento operacional sem defeitos",
        "criteria": [
            "Liga e funciona normalmente",
            "Sem danos físicos significativos",
            "Todos os componentes presentes",
            "Passa nos testes funcionais",
        ],
        "depot_action": "Retorna ao estoque ativo",
    },
    "DEFEITUOSO": {
        "description": "Equipamento com defeito reparável",
        "criteria": [
            "Não liga ou funciona parcialmente",
            "Danos físicos reparáveis",
            "Faltando componentes substituíveis",
            "Falha em testes funcionais",
        ],
        "depot_action": "Encaminha para reparo (BAD)",
    },
    "INSERVIVEL": {
        "description": "Equipamento sem possibilidade de reparo",
        "criteria": [
            "Danos irreparáveis",
            "Custo de reparo > valor do equipamento",
            "Obsoleto sem peças disponíveis",
            "Risco de segurança",
        ],
        "depot_action": "Encaminha para descarte (requer aprovação)",
    },
}


# =============================================================================
# Tool Implementation
# =============================================================================


async def evaluate_condition_tool(
    serial_number: str,
    inspection_notes: str = "",
    test_results: Optional[Dict[str, Any]] = None,
    photos: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    AI-assisted evaluation of equipment condition for return processing.

    Uses Gemini to analyze:
    1. Inspection notes provided by operator
    2. Test results (if available)
    3. Equipment history
    4. Photos (if provided)

    Returns a recommended condition with confidence score.
    Low confidence triggers HIL for human decision.

    Args:
        serial_number: Equipment serial number
        inspection_notes: Free-text notes from physical inspection
        test_results: Structured test results (key-value pairs)
        photos: List of photo URLs/S3 keys (future implementation)
        session_id: Session ID for audit trail

    Returns:
        Dict with condition evaluation and recommendation
    """
    from shared.audit_emitter import AgentAuditEmitter

    audit = AgentAuditEmitter(agent_id="reverse")

    audit.working(
        f"Avaliando condição: {serial_number}",
        session_id=session_id,
    )

    try:
        if not serial_number:
            return {
                "success": False,
                "error": "Serial number é obrigatório",
            }

        # Get equipment history
        equipment = await _lookup_equipment(serial_number)
        history = await _get_repair_history(serial_number)

        # Analyze with AI
        evaluation = await _ai_evaluate_condition(
            serial_number=serial_number,
            equipment=equipment,
            history=history,
            inspection_notes=inspection_notes,
            test_results=test_results,
        )

        # Determine if HIL required
        confidence = evaluation.get("confidence", 0.0)
        recommended_condition = evaluation.get("recommended_condition", "DEFEITUOSO")

        # HIL triggers:
        # 1. Low confidence (<70%)
        # 2. INSERVIVEL recommendation (always needs approval)
        # 3. Conflicting signals
        requires_hil = (
            confidence < 0.7
            or recommended_condition == "INSERVIVEL"
            or evaluation.get("conflicting_signals", False)
        )

        hil_task_id = None
        if requires_hil:
            hil_task_id = str(uuid.uuid4())
            audit.working(
                "Avaliação requer revisão humana (HIL)",
                session_id=session_id,
                details={
                    "hil_task_id": hil_task_id,
                    "reason": "low_confidence" if confidence < 0.7 else "inservivel_recommendation",
                },
            )

        # Prepare detailed report
        condition_info = CONDITION_CRITERIA.get(recommended_condition, {})

        audit.completed(
            f"Condição avaliada: {recommended_condition} (confiança: {confidence:.0%})",
            session_id=session_id,
            details={
                "condition": recommended_condition,
                "confidence": confidence,
                "requires_hil": requires_hil,
            },
        )

        return {
            "success": True,
            "evaluation": {
                "serial_number": serial_number,
                "recommended_condition": recommended_condition,
                "condition_description": condition_info.get("description"),
                "depot_action": condition_info.get("depot_action"),
                "confidence": confidence,
                "confidence_percent": f"{confidence:.0%}",
                "reasoning": evaluation.get("reasoning", ""),
                "factors": evaluation.get("factors", []),
            },
            "equipment_context": {
                "part_number": equipment.get("part_number") if equipment else None,
                "age_days": equipment.get("age_days") if equipment else None,
                "repair_count": len(history) if history else 0,
            },
            "requires_hil": requires_hil,
            "hil_task_id": hil_task_id,
            "hil_reason": _get_hil_reason(confidence, recommended_condition) if requires_hil else None,
            "condition_options": [
                {
                    "condition": cond,
                    "description": info["description"],
                    "criteria": info["criteria"],
                }
                for cond, info in CONDITION_CRITERIA.items()
            ],
        }

    except Exception as e:
        logger.error(f"[evaluate_condition] Error: {e}", exc_info=True)
        audit.error(
            f"Erro ao avaliar condição: {serial_number}",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _lookup_equipment(serial_number: str) -> Optional[Dict[str, Any]]:
    """Look up equipment details."""
    # Simulate
    return {
        "id": str(uuid.uuid4()),
        "serial_number": serial_number,
        "part_number": "PN-12345",
        "description": "Equipment",
        "age_days": 365,
    }


async def _get_repair_history(serial_number: str) -> List[Dict[str, Any]]:
    """Get repair history for equipment."""
    # Simulate - in production query movements where type=CONSERTO
    return [
        {
            "repair_id": str(uuid.uuid4()),
            "date": "2024-06-15",
            "issue": "Display não funcionava",
            "resolution": "Substituição do display",
            "cost": 150.00,
        }
    ]


async def _ai_evaluate_condition(
    serial_number: str,
    equipment: Optional[Dict[str, Any]],
    history: List[Dict[str, Any]],
    inspection_notes: str,
    test_results: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Use AI (Gemini) to evaluate equipment condition.

    In production, this would call Gemini with a structured prompt.
    For now, uses rule-based heuristics.
    """
    factors = []
    confidence = 0.8  # Base confidence

    # Analyze inspection notes
    notes_lower = inspection_notes.lower() if inspection_notes else ""

    # Keywords indicating functional
    functional_keywords = ["funciona", "ok", "bom estado", "operacional", "normal"]
    # Keywords indicating defective
    defective_keywords = ["não liga", "defeito", "quebrado", "falha", "danificado", "não funciona"]
    # Keywords indicating unserviceable
    unserviceable_keywords = ["irreparável", "sucata", "descarte", "inservível", "perda total"]

    functional_score = sum(1 for kw in functional_keywords if kw in notes_lower)
    defective_score = sum(1 for kw in defective_keywords if kw in notes_lower)
    unserviceable_score = sum(1 for kw in unserviceable_keywords if kw in notes_lower)

    # Check repair history
    repair_count = len(history) if history else 0
    if repair_count >= 3:
        factors.append(f"Histórico de {repair_count} reparos anteriores (risco de reincidência)")
        defective_score += 1

    # Check test results
    if test_results:
        failed_tests = [k for k, v in test_results.items() if v in [False, "FAIL", "FAILED", "NOK"]]
        if failed_tests:
            factors.append(f"Testes falhados: {', '.join(failed_tests)}")
            defective_score += len(failed_tests)

    # Determine condition based on scores
    if unserviceable_score > 0:
        recommended = "INSERVIVEL"
        factors.append("Identificados indicadores de equipamento inservível")
        confidence = 0.6 if defective_score > 0 or functional_score > 0 else 0.8
    elif defective_score > functional_score:
        recommended = "DEFEITUOSO"
        factors.append("Identificados indicadores de defeito")
        confidence = 0.85 if functional_score == 0 else 0.65
    elif functional_score > 0:
        recommended = "FUNCIONAL"
        factors.append("Identificados indicadores de funcionamento normal")
        confidence = 0.9 if defective_score == 0 else 0.7
    else:
        # No clear indicators - default to DEFEITUOSO and request HIL
        recommended = "DEFEITUOSO"
        factors.append("Sem indicadores claros - recomendada inspeção detalhada")
        confidence = 0.5

    # Check for conflicting signals
    conflicting = (functional_score > 0 and defective_score > 0) or \
                  (functional_score > 0 and unserviceable_score > 0)

    reasoning = f"Baseado na análise: {functional_score} indicadores positivos, " \
                f"{defective_score} indicadores de defeito, " \
                f"{unserviceable_score} indicadores de inservibilidade."

    return {
        "recommended_condition": recommended,
        "confidence": confidence,
        "reasoning": reasoning,
        "factors": factors,
        "conflicting_signals": conflicting,
    }


def _get_hil_reason(confidence: float, condition: str) -> str:
    """Get human-readable HIL reason."""
    reasons = []
    if confidence < 0.7:
        reasons.append(f"Confiança baixa ({confidence:.0%})")
    if condition == "INSERVIVEL":
        reasons.append("Descarte requer aprovação obrigatória")
    return " | ".join(reasons) if reasons else "Revisão requerida"
