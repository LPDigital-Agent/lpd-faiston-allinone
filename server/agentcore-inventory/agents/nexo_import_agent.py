# =============================================================================
# NexoImportAgent - Shim Class for Strands A2A Migration
# =============================================================================
# This module provides the NexoImportAgent class expected by main_a2a.py.
# It wraps the existing tool implementations from agents/nexo_import/tools/.
#
# Created during Day 5 CLEANUP of Strands A2A migration.
# =============================================================================

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class NexoImportAgent:
    """
    NexoImportAgent shim class for Strands A2A.

    Wraps the existing Google ADK tool implementations to provide
    the interface expected by main_a2a.py @tool decorated functions.

    Expected interface:
    - analyze_file(): Analyze file structure from S3
    - execute_import(): Execute import with validated mappings
    - submit_answers(): Process HIL (Human-in-the-Loop) answers
    """

    def __init__(self):
        """Initialize the agent."""
        self.agent_id = "nexo_import"
        self.agent_name = "NexoImportAgent"
        logger.info(f"[{self.agent_name}] Initialized (Strands A2A shim)")

    async def analyze_file(
        self,
        file_key: str = None,
        file_name: str = None,
        file_type: str = None,
        user_id: str = None,
        session_id: str = None,
        s3_key: str = None,
        filename: str = None,
    ) -> Dict[str, Any]:
        """
        Analyze file structure from S3.

        Wraps agents.nexo_import.tools.analyze_file.analyze_file_tool
        """
        # Normalize parameters (support both naming conventions)
        actual_s3_key = s3_key or file_key
        actual_filename = filename or file_name

        try:
            from agents.nexo_import.tools.analyze_file import analyze_file_tool

            result = await analyze_file_tool(
                s3_key=actual_s3_key,
                filename=actual_filename,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] analyze_file failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_key": actual_s3_key,
            }

    async def execute_import(
        self,
        analysis_id: str = None,
        user_id: str = None,
        session_id: str = None,
        column_mapping: Dict[str, str] = None,
        target_table: str = None,
        s3_key: str = None,
        column_mappings: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Execute import with validated column mappings.

        Wraps agents.nexo_import.tools.execute_import.execute_import_tool
        """
        # Normalize parameters
        actual_mappings = column_mappings or column_mapping or {}
        actual_table = target_table or "pending_entry_items"
        actual_s3_key = s3_key or analysis_id  # analysis_id might be the s3_key

        try:
            from agents.nexo_import.tools.execute_import import execute_import_tool

            result = await execute_import_tool(
                s3_key=actual_s3_key,
                column_mappings=actual_mappings,
                target_table=actual_table,
                user_id=user_id,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] execute_import failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "rows_imported": 0,
            }

    async def submit_answers(
        self,
        analysis_id: str = None,
        answers: Dict[str, Any] = None,
        session_id: str = None,
        user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Process HIL (Human-in-the-Loop) answers.

        Updates column mappings based on user answers and determines
        if the analysis is ready for import execution.
        """
        try:
            # For now, simple passthrough - answers update the mappings directly
            # In future, this should delegate to a proper answer processing tool

            if not answers:
                return {
                    "success": True,
                    "ready_for_import": True,
                    "message": "No answers to process",
                }

            # Process answers - typically these are mapping confirmations
            processed_mappings = {}
            remaining_questions = []

            for question_id, answer in answers.items():
                if isinstance(answer, dict):
                    # Answer contains mapping decision
                    source = answer.get("source_column")
                    target = answer.get("target_field")
                    if source and target:
                        processed_mappings[source] = target
                else:
                    # Simple answer - assume it's the target field
                    processed_mappings[question_id] = answer

            return {
                "success": True,
                "ready_for_import": len(remaining_questions) == 0,
                "updated_mappings": processed_mappings,
                "remaining_questions": remaining_questions,
                "message": f"Processed {len(processed_mappings)} answer(s)",
            }

        except Exception as e:
            logger.error(f"[{self.agent_name}] submit_answers failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "ready_for_import": False,
            }

    async def reason_mappings(
        self,
        file_analysis: Dict[str, Any],
        schema_context: Dict[str, Any] = None,
        prior_knowledge: Dict[str, Any] = None,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Reason about column mappings using schema context.

        Wraps agents.nexo_import.tools.reason_mappings.reason_mappings_tool
        """
        try:
            from agents.nexo_import.tools.reason_mappings import reason_mappings_tool

            result = await reason_mappings_tool(
                file_analysis=file_analysis,
                schema_context=schema_context,
                prior_knowledge=prior_knowledge,
            )

            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] reason_mappings failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "mappings": {},
            }

    async def generate_questions(
        self,
        mappings: Dict[str, Any],
        confidence_threshold: float = 0.8,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generate HIL questions for low-confidence mappings.

        Wraps agents.nexo_import.tools.generate_questions.generate_questions_tool
        """
        try:
            from agents.nexo_import.tools.generate_questions import generate_questions_tool

            result = await generate_questions_tool(
                mappings=mappings,
                confidence_threshold=confidence_threshold,
            )

            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] generate_questions failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "questions": [],
            }


# Export for import compatibility
__all__ = ["NexoImportAgent"]
