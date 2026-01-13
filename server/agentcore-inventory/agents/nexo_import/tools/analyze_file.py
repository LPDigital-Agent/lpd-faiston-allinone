# =============================================================================
# Analyze File Tool - AI-First with Gemini Pro (AGI-Like Behavior)
# =============================================================================
# Analyzes file structure (sheets, columns, types) from S3 using Gemini.
#
# Philosophy: OBSERVE → THINK → LEARN → EXECUTE (with Multi-Round HIL)
# - OBSERVE: Download file from S3
# - THINK: Gemini Pro analyzes semantically with context
# - LEARN: Uses memory context from LearningAgent (AgentCore Memory)
# - EXECUTE: Returns analysis with confidence and HIL questions
#
# AGI-Like Behavior:
# - Multi-round iterative HIL dialogue
# - User responses feed back into Gemini for re-analysis
# - Unmapped columns are flagged and require user decision
# - Final summary requires explicit user approval before import
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# =============================================================================

import logging
from typing import Dict, Any, Optional, List


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
    user_responses: Optional[List[Dict[str, Any]]] = None,
    user_comments: Optional[str] = None,
    analysis_round: int = 1,
) -> Dict[str, Any]:
    """
    Analyze file structure from S3 using Gemini Pro (AI-First with AGI-Like Behavior).

    Examines the file to determine:
    - Column names and suggested mappings
    - Confidence scores for each mapping
    - HIL questions for low-confidence mappings
    - Unmapped columns requiring user decision
    - Row counts and data types

    AGI-Like Multi-Round HIL:
    - Round 1: Initial analysis (Memory + File + Schema)
    - Round 2+: Re-analysis with user responses (Memory + File + Schema + Responses)
    - Continues until ready_for_import=True

    Args:
        s3_key: S3 key where file is stored
        filename: Original filename for pattern matching
        session_id: Optional session ID for audit
        schema_context: PostgreSQL schema description (optional)
        memory_context: Learned patterns from LearningAgent (optional)
        user_responses: User answers from previous HIL rounds (AGI-like)
        user_comments: Free-text instructions from user (AGI-like)
        analysis_round: Current round number (1 = first, 2+ = re-analysis)

    Returns:
        File analysis with structure, mappings, HIL questions, and readiness status
    """
    round_label = f"Round {analysis_round}"
    if user_responses:
        audit.working(
            message=f"[{round_label}] Re-analisando com {len(user_responses)} respostas: {filename or s3_key}",
            session_id=session_id,
        )
    else:
        audit.working(
            message=f"[{round_label}] Analisando arquivo com Gemini: {filename or s3_key}",
            session_id=session_id,
        )

    try:
        # AI-First: Use Gemini for semantic analysis (AGI-like with user context)
        from tools.gemini_text_analyzer import analyze_file_with_gemini

        analysis = await analyze_file_with_gemini(
            s3_key=s3_key,
            schema_context=schema_context,
            memory_context=memory_context,
            user_responses=user_responses,
            user_comments=user_comments,
            analysis_round=analysis_round,
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

        # AGI-like fields
        unmapped_columns = analysis.get("unmapped_columns", [])
        unmapped_questions = analysis.get("unmapped_questions", [])
        all_questions_answered = analysis.get("all_questions_answered", False)
        ready_for_import = analysis.get("ready_for_import", False)
        current_round = analysis.get("analysis_round", analysis_round)

        # Calculate total pending questions
        total_pending = len(hil_questions) + len(unmapped_questions)

        # Determine status message
        if ready_for_import:
            status_msg = f"[{round_label}] Pronto para importação: {row_count} linhas"
        elif total_pending > 0:
            status_msg = f"[{round_label}] Aguardando {total_pending} resposta(s)"
        else:
            status_msg = f"[{round_label}] Análise: {row_count} linhas, confiança {confidence:.0%}"

        audit.completed(
            message=status_msg,
            session_id=session_id,
            details={
                "row_count": row_count,
                "column_count": column_count,
                "confidence": confidence,
                "recommended_action": recommended_action,
                "hil_questions_count": len(hil_questions),
                "unmapped_columns_count": len(unmapped_columns),
                "ready_for_import": ready_for_import,
                "analysis_round": current_round,
            },
        )

        # Determine if agent should stop and wait for user response
        # CRITICAL: This flag tells the Strands ReAct loop to pause
        should_stop = total_pending > 0 or not ready_for_import

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
            # AGI-like fields
            "unmapped_columns": unmapped_columns,
            "unmapped_questions": unmapped_questions,
            "all_questions_answered": all_questions_answered,
            "ready_for_import": ready_for_import,
            "analysis_round": current_round,
            "pending_questions_count": total_pending,
            # STOP ACTION: Signal Strands ReAct to pause for user response
            "stop_action": should_stop,
            "stop_reason": "Aguardando respostas do usuário" if should_stop else None,
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
