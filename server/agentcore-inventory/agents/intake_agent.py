# =============================================================================
# IntakeAgent - Shim Class for Strands A2A Migration
# =============================================================================
# This module provides the IntakeAgent class expected by main_a2a.py.
# It wraps the existing tool implementations from agents/intake/tools/.
#
# Created during Day 5 CLEANUP of Strands A2A migration.
# =============================================================================

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class IntakeAgent:
    """
    IntakeAgent shim class for Strands A2A.

    Wraps the existing Google ADK tool implementations to provide
    the interface expected by main_a2a.py @tool decorated functions.

    Expected interface:
    - process_nf(): Process NF (Nota Fiscal) upload and extract data
    """

    def __init__(self):
        """Initialize the agent."""
        self.agent_id = "intake"
        self.agent_name = "IntakeAgent"
        logger.info(f"[{self.agent_name}] Initialized (Strands A2A shim)")

    async def process_nf(
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
        Process NF (Nota Fiscal) upload.

        This is the main entry point for NF processing:
        1. Parse the NF XML/PDF from S3
        2. Extract header and item data
        3. Match items to existing part numbers
        4. Create pending entry for review

        Wraps multiple tools from agents.intake.tools
        """
        # Normalize parameters
        actual_s3_key = s3_key or file_key
        actual_filename = filename or file_name

        try:
            # Step 1: Parse the NF file
            from agents.intake.tools.parse_nf import parse_nf_tool

            parse_result = await parse_nf_tool(
                s3_key=actual_s3_key,
                filename=actual_filename,
                file_type=file_type,
                session_id=session_id,
            )

            if not parse_result.get("success"):
                return {
                    "success": False,
                    "error": parse_result.get("error", "Failed to parse NF"),
                    "file_key": actual_s3_key,
                }

            nf_data = parse_result.get("nf_data", {})
            items = nf_data.get("items", [])

            if not items:
                return {
                    "success": False,
                    "error": "NF parsed but no items found",
                    "nf_data": nf_data,
                    "file_key": actual_s3_key,
                }

            # Step 2: Match items to part numbers
            from agents.intake.tools.match_items import match_items_tool

            match_result = await match_items_tool(
                items=items,
                session_id=session_id,
            )

            matched_items = match_result.get("matched_items", items)

            # Step 3: Process the entry
            from agents.intake.tools.process_entry import process_entry_tool

            entry_result = await process_entry_tool(
                nf_data=nf_data,
                matched_items=matched_items,
                user_id=user_id,
                session_id=session_id,
            )

            return {
                "success": entry_result.get("success", False),
                "entry_id": entry_result.get("entry_id"),
                "nf_number": nf_data.get("nf_number"),
                "supplier": nf_data.get("supplier_name"),
                "items_count": len(items),
                "items_matched": match_result.get("matched_count", 0),
                "items_pending_review": match_result.get("pending_review_count", 0),
                "message": entry_result.get("message"),
                "nf_data": nf_data,
            }

        except Exception as e:
            logger.error(f"[{self.agent_name}] process_nf failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "file_key": actual_s3_key,
            }

    async def confirm_entry(
        self,
        entry_id: str,
        user_id: str = None,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Confirm a pending entry and create movements.

        Wraps agents.intake.tools.confirm_entry.confirm_entry_tool
        """
        try:
            from agents.intake.tools.confirm_entry import confirm_entry_tool

            result = await confirm_entry_tool(
                entry_id=entry_id,
                user_id=user_id,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] confirm_entry failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "entry_id": entry_id,
            }


# Export for import compatibility
__all__ = ["IntakeAgent"]
