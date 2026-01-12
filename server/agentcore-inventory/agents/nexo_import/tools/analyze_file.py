# =============================================================================
# Analyze File Tool
# =============================================================================
# Analyzes file structure (sheets, columns, types) from S3.
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
) -> Dict[str, Any]:
    """
    Analyze file structure from S3.

    Examines the file to determine:
    - Number of sheets (for Excel/multi-sheet files)
    - Column names and sample data
    - Detected data types
    - Row counts

    Args:
        s3_key: S3 key where file is stored
        filename: Original filename for pattern matching
        session_id: Optional session ID for audit

    Returns:
        File analysis with structure information
    """
    audit.working(
        message=f"Analisando arquivo: {filename or s3_key}",
        session_id=session_id,
    )

    try:
        from tools.sheet_analyzer import SheetAnalyzer

        analyzer = SheetAnalyzer()
        analysis = await analyzer.analyze_from_s3(s3_key)

        audit.completed(
            message=f"Análise concluída: {analysis.get('sheet_count', 1)} planilha(s)",
            session_id=session_id,
            details={
                "sheet_count": analysis.get("sheet_count", 1),
                "total_rows": analysis.get("total_rows", 0),
            },
        )

        return {
            "success": True,
            "file_analysis": analysis,
            "sheet_count": analysis.get("sheet_count", 1),
            "total_rows": analysis.get("total_rows", 0),
            "sheets": analysis.get("sheets", []),
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
