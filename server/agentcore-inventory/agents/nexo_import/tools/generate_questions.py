# =============================================================================
# Generate Questions Tool
# =============================================================================
# Generates HIL (Human-in-the-Loop) questions for low-confidence mappings.
# =============================================================================

import logging
from typing import Dict, Any, List, Optional


from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)

AGENT_ID = "nexo_import"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@trace_tool_call("sga_generate_questions")
async def generate_questions_tool(
    needs_clarification: List[Dict[str, Any]],
    schema_context: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate HIL questions for columns needing clarification.

    Builds intelligent questions for columns where:
    - Confidence < 80% (threshold for autonomous action)
    - No prior knowledge exists
    - Multiple possible mappings exist

    Args:
        needs_clarification: List of columns needing user input
        schema_context: PostgreSQL schema markdown for context
        session_id: Optional session ID for audit

    Returns:
        Generated questions for HIL review
    """
    audit.working(
        message=f"Gerando {len(needs_clarification)} pergunta(s)...",
        session_id=session_id,
    )

    try:
        questions = []

        # Parse available fields from schema context
        available_fields = _extract_fields_from_schema(schema_context)

        for item in needs_clarification:
            column = item.get("column", "")
            suggested_field = item.get("suggested_field")
            confidence = item.get("confidence", 0.0)
            reason = item.get("reason", "")

            if not column:
                continue

            # Build question based on situation
            question = _build_question(
                column=column,
                suggested_field=suggested_field,
                confidence=confidence,
                reason=reason,
                available_fields=available_fields,
            )

            if question:
                questions.append(question)

        audit.completed(
            message=f"Geradas {len(questions)} pergunta(s) para revisão",
            session_id=session_id,
            details={"question_count": len(questions)},
        )

        return {
            "success": True,
            "questions": questions,
            "total_questions": len(questions),
            "available_fields": available_fields,
        }

    except Exception as e:
        logger.error(f"[generate_questions] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao gerar perguntas",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
            "questions": [],
        }


def _extract_fields_from_schema(schema_context: str) -> List[str]:
    """
    Extract available fields from schema context.

    Returns list of field names from pending_entry_items table.
    """
    # Standard fields in pending_entry_items
    standard_fields = [
        "part_number",
        "description",
        "quantity",
        "serial_number",
        "location",
        "unit",
        "condition",
        "notes",
        "project_code",
        "batch_number",
        "manufacturer",
        "supplier",
    ]

    # Try to parse additional fields from schema context
    additional_fields = []
    if schema_context:
        # Look for column definitions
        lines = schema_context.split("\n")
        for line in lines:
            line_lower = line.lower().strip()
            if "column" in line_lower or "|" in line:
                # Try to extract column name from markdown table or text
                parts = line.split("|")
                if len(parts) >= 2:
                    potential_field = parts[1].strip().lower()
                    if potential_field and potential_field not in standard_fields:
                        if potential_field.isidentifier():
                            additional_fields.append(potential_field)

    return standard_fields + additional_fields


def _build_question(
    column: str,
    suggested_field: Optional[str],
    confidence: float,
    reason: str,
    available_fields: List[str],
) -> Dict[str, Any]:
    """
    Build a structured question for HIL review.

    Returns question dict with type, options, and context.
    """
    question_id = f"q_{column.lower().replace(' ', '_')}"

    if suggested_field and confidence >= 0.5:
        # Medium confidence - ask to confirm suggestion
        return {
            "id": question_id,
            "type": "confirmation",
            "column": column,
            "question": f"A coluna '{column}' parece corresponder ao campo '{suggested_field}'. Confirma?",
            "suggested_field": suggested_field,
            "confidence": confidence,
            "reason": reason,
            "options": [
                {"value": suggested_field, "label": f"Sim, mapear para '{suggested_field}'"},
                {"value": "_select_other", "label": "Não, escolher outro campo"},
                {"value": "_skip", "label": "Ignorar esta coluna"},
                {"value": "_create_new", "label": "Criar nova coluna"},
            ],
            "available_fields": available_fields,
        }

    elif suggested_field:
        # Low confidence - show suggestion but ask for selection
        return {
            "id": question_id,
            "type": "selection",
            "column": column,
            "question": f"Para qual campo a coluna '{column}' deve ser mapeada?",
            "suggested_field": suggested_field,
            "confidence": confidence,
            "reason": reason,
            "options": _build_field_options(available_fields, suggested_field),
            "available_fields": available_fields,
        }

    else:
        # No suggestion - ask for mapping
        return {
            "id": question_id,
            "type": "mapping",
            "column": column,
            "question": f"A coluna '{column}' não foi reconhecida. Para qual campo deve ser mapeada?",
            "suggested_field": None,
            "confidence": 0.0,
            "reason": reason,
            "options": _build_field_options(available_fields, None),
            "available_fields": available_fields,
        }


def _build_field_options(
    available_fields: List[str],
    suggested_field: Optional[str],
) -> List[Dict[str, str]]:
    """
    Build options list for field selection.

    Puts suggested field first if provided.
    """
    options = []

    # Add suggested field first with indicator
    if suggested_field and suggested_field in available_fields:
        options.append({
            "value": suggested_field,
            "label": f"{suggested_field} (sugerido)",
        })

    # Add other fields
    for field in available_fields:
        if field != suggested_field:
            options.append({
                "value": field,
                "label": field,
            })

    # Add special options
    options.extend([
        {"value": "_skip", "label": "Ignorar esta coluna"},
        {"value": "_create_new", "label": "Criar nova coluna"},
    ])

    return options
