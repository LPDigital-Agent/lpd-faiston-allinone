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
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4

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
            # Extract detailed error information for debugging
            error_detail = analysis.get("error", "Unknown error")
            analysis_keys = list(analysis.keys()) if isinstance(analysis, dict) else []

            # Log full analysis response for debugging (critical for troubleshooting)
            logger.error(
                f"[analyze_file] Gemini analysis failed. "
                f"Error: {error_detail}. "
                f"Analysis keys: {analysis_keys}. "
                f"Raw response preview: {str(analysis)[:500]}"
            )

            audit.error(
                message=f"Falha na análise com Gemini: {error_detail}",
                session_id=session_id,
                error=f"Keys: {analysis_keys}",
            )

            return {
                "success": False,
                "error": error_detail,
                "file_analysis": {},
                "sheets": [],
                "debug_gemini_response_keys": analysis_keys,
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

        # Generate session ID if not provided
        effective_session_id = session_id or f"nexo-{uuid4().hex[:8]}"
        effective_filename = filename or s3_key.split("/")[-1]

        # Build column_mappings array (matches TypeScript NexoColumnMapping[])
        column_mappings = [
            {
                "file_column": col.get("source_name", col.get("name", "")),
                "target_field": col.get("suggested_mapping") or col.get("target_field", ""),
                "confidence": col.get("mapping_confidence", col.get("confidence", 0.0)),
                "reasoning": col.get("reason", f"Mapped based on column name pattern"),
                "alternatives": [],
            }
            for col in analysis.get("columns", [])
            if col.get("suggested_mapping") or col.get("target_field")
        ]

        # Build questions array (matches TypeScript NexoQuestion[])
        questions = [
            {
                "id": q.get("id", f"q{i}"),
                "question": q.get("question", ""),
                "context": q.get("reason", q.get("context", "")),
                "importance": "critical" if q.get("priority") == "high" else "medium",
                "topic": q.get("topic", "column_mapping"),
                "options": [
                    {"value": opt if isinstance(opt, str) else opt.get("value", ""),
                     "label": opt if isinstance(opt, str) else opt.get("label", "")}
                    for opt in q.get("options", [])
                ] if q.get("options") else [],
                "default_value": q.get("default_value"),
            }
            for i, q in enumerate(hil_questions)
        ]

        # Build unmapped_questions array (matches TypeScript)
        unmapped_questions_formatted = [
            {
                "id": uq.get("id", f"uq{i}"),
                "type": "unmapped",
                "column": uq.get("field", uq.get("column", "")),
                "question": uq.get("question", ""),
                "description": uq.get("reason", uq.get("description", "")),
                "suggested_action": uq.get("suggested_action", "metadata"),
                "options": [
                    {"value": opt if isinstance(opt, str) else opt.get("value", ""),
                     "label": opt if isinstance(opt, str) else opt.get("label", ""),
                     "warning": opt.get("warning", False) if isinstance(opt, dict) else False,
                     "recommended": opt.get("recommended", False) if isinstance(opt, dict) else False}
                    for opt in uq.get("options", [])
                ] if uq.get("options") else [],
                "blocking": True,
            }
            for i, uq in enumerate(unmapped_questions)
        ]

        # Build reasoning_trace (matches TypeScript NexoReasoningStep[])
        reasoning_trace = [
            {
                "type": "observation",
                "content": f"Analyzed file: {effective_filename}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "type": "thought",
                "content": f"Detected {column_count} columns, {row_count} rows with {confidence:.0%} confidence",
            },
            {
                "type": "action",
                "content": f"Recommended action: {recommended_action}",
                "tool": "gemini_text_analyzer",
            },
        ]

        # Build nested analysis object (CRITICAL - matches TypeScript NexoAnalyzeFileResponse.analysis)
        analysis_nested = {
            "sheet_count": 1,
            "total_rows": row_count,
            "sheets": [{
                "name": analysis.get("filename", "Sheet1"),
                "purpose": "items",  # Default purpose for single-sheet files
                "row_count": row_count,
                "column_count": column_count,
                "columns": [
                    {
                        "name": col.get("source_name", col.get("name", "")),
                        "sample_values": col.get("sample_values", []),
                        "detected_type": col.get("data_type", col.get("detected_type", "string")),
                        "suggested_mapping": col.get("suggested_mapping") or col.get("target_field"),
                        "confidence": col.get("mapping_confidence", col.get("confidence", 0.0)),
                    }
                    for col in analysis.get("columns", [])
                ],
                "confidence": confidence,
            }],
            "recommended_strategy": recommended_action,
        }

        return {
            # Core response fields (matches TypeScript NexoAnalyzeFileResponse)
            "success": True,
            "import_session_id": effective_session_id,
            "filename": effective_filename,
            "detected_file_type": analysis.get("file_type", "csv"),

            # NESTED analysis object (CRITICAL - matches TypeScript contract)
            "analysis": analysis_nested,

            # Column mappings array
            "column_mappings": column_mappings,

            # Overall confidence (renamed from confidence)
            "overall_confidence": confidence,

            # Questions array (renamed from hil_questions)
            "questions": questions,

            # Unmapped questions for AGI-like behavior
            "unmapped_questions": unmapped_questions_formatted if unmapped_questions_formatted else None,

            # Reasoning trace for transparency
            "reasoning_trace": reasoning_trace,

            # Session IDs
            "user_id": None,  # Set by orchestrator if needed
            "session_id": effective_session_id,

            # STATELESS: Session state for frontend storage
            "session_state": {
                "session_id": effective_session_id,
                "filename": effective_filename,
                "s3_key": s3_key,
                "stage": "questioning" if total_pending > 0 else "processing",
                "file_analysis": {
                    "sheets": analysis_nested["sheets"],
                    "sheet_count": 1,
                    "total_rows": row_count,
                    "detected_type": analysis.get("file_type", "csv"),
                    "recommended_strategy": recommended_action,
                },
                "reasoning_trace": reasoning_trace,
                "questions": questions,
                "answers": {},
                "learned_mappings": {},
                "ai_instructions": {},
                "requested_new_columns": [],
                "column_mappings": {
                    m["file_column"]: m["target_field"]
                    for m in column_mappings
                },
                "confidence": {
                    "overall": confidence,
                    "extraction_quality": 1.0,
                    "evidence_strength": 1.0,
                    "historical_match": 1.0,
                    "risk_level": "low" if confidence >= 0.8 else "medium" if confidence >= 0.5 else "high",
                    "factors": [],
                    "requires_hil": confidence < 0.6,
                },
                "error": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },

            # AGI-like control fields (for internal use)
            "ready_for_import": ready_for_import,
            "analysis_round": current_round,
            "pending_questions_count": total_pending,

            # Strands ReAct control
            "stop_action": should_stop,
            "stop_reason": "Aguardando respostas do usuário" if should_stop else None,

            # DEPRECATED: Legacy fields for backward compatibility
            "file_analysis": analysis,  # Keep for debugging
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
