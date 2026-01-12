# =============================================================================
# Analyze File Tool - AI-First with Gemini Pro
# =============================================================================
# Analyzes file structure (sheets, columns, types) from S3 using Gemini.
#
# Philosophy: OBSERVE → THINK → LEARN → EXECUTE
# - OBSERVE: Download file from S3
# - THINK: Gemini Pro analyzes semantically
# - LEARN: Uses memory context from LearningAgent
# - EXECUTE: Returns analysis with confidence and HIL questions
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# =============================================================================

import logging
from typing import Dict, Any, Optional


from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)

AGENT_ID = "nexo_import"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@trace_tool_call("sga_analyze_file")
async def analyze_file_tool(
    s3_key: str,
    filename: Optional[str] = None,
    session_id: Optional[str] = None,
    schema_context: Optional[str] = None,
    memory_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze file structure from S3 using Gemini Pro (AI-First).

    Examines the file to determine:
    - Column names and suggested mappings
    - Confidence scores for each mapping
    - HIL questions for low-confidence mappings
    - Row counts and data types

    Args:
        s3_key: S3 key where file is stored
        filename: Original filename for pattern matching
        session_id: Optional session ID for audit
        schema_context: PostgreSQL schema description (optional)
        memory_context: Learned patterns from LearningAgent (optional)

    Returns:
        File analysis with structure, mappings, and HIL questions
    """
    audit.working(
        message=f"Analisando arquivo com Gemini: {filename or s3_key}",
        session_id=session_id,
    )

    try:
        # AI-First: Use Gemini for semantic analysis
        from tools.gemini_text_analyzer import analyze_file_with_gemini

        analysis = await analyze_file_with_gemini(
            s3_key=s3_key,
            schema_context=schema_context,
            memory_context=memory_context,
        )

        if not analysis.get("success", False):
            audit.error(
                message="Falha na análise com Gemini",
                session_id=session_id,
                error=analysis.get("error", "Unknown error"),
            )
            return {
                "success": False,
                "error": analysis.get("error", "Analysis failed"),
                "file_analysis": {},
                "sheets": [],
            }

        # Extract key metrics
        row_count = analysis.get("row_count", 0)
        column_count = analysis.get("column_count", 0)
        confidence = analysis.get("analysis_confidence", 0.0)
        recommended_action = analysis.get("recommended_action", "unknown")
        hil_questions = analysis.get("hil_questions", [])

        audit.completed(
            message=f"Análise concluída: {row_count} linhas, confiança {confidence:.0%}",
            session_id=session_id,
            details={
                "row_count": row_count,
                "column_count": column_count,
                "confidence": confidence,
                "recommended_action": recommended_action,
                "hil_questions_count": len(hil_questions),
            },
        )

        return {
            "success": True,
            "file_analysis": analysis,
            "row_count": row_count,
            "column_count": column_count,
            "confidence": confidence,
            "columns": analysis.get("columns", []),
            "suggested_mappings": analysis.get("suggested_mappings", {}),
            "hil_questions": hil_questions,
            "recommended_action": recommended_action,
            # Legacy fields for compatibility
            "sheet_count": 1,
            "total_rows": row_count,
            "sheets": [{
                "name": analysis.get("filename", "Sheet1"),
                "row_count": row_count,
                "column_count": column_count,
                "columns": analysis.get("columns", []),
            }],
        }

    except Exception as e:
        logger.error(f"[analyze_file] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao analisar arquivo",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
            "file_analysis": {},
            "sheets": [],
        }


# Alias for backward compatibility with main.py imports
analyze_file_impl = analyze_file_tool
