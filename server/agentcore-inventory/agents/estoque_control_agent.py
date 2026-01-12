# =============================================================================
# EstoqueControlAgent - Shim Class for Strands A2A Migration
# =============================================================================
# This module provides the EstoqueControlAgent class expected by main_a2a.py.
# It wraps the existing tool implementations from agents/estoque_control/tools/.
#
# Created during Day 5 CLEANUP of Strands A2A migration.
# =============================================================================

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class EstoqueControlAgent:
    """
    EstoqueControlAgent shim class for Strands A2A.

    Wraps the existing Google ADK tool implementations to provide
    the interface expected by main_a2a.py @tool decorated functions.

    Expected interface:
    - create_movement(): Create inventory movement
    - query_balance(): Query stock balance
    """

    def __init__(self):
        """Initialize the agent."""
        self.agent_id = "estoque_control"
        self.agent_name = "EstoqueControlAgent"
        logger.info(f"[{self.agent_name}] Initialized (Strands A2A shim)")

    async def create_movement(
        self,
        movement_type: str,
        asset_id: str = None,
        part_number: str = None,
        quantity: float = 1,
        from_location: str = None,
        to_location: str = None,
        project_id: str = None,
        reference: str = None,
        notes: str = None,
        user_id: str = None,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Create an inventory movement.

        Supports movement types:
        - ENTRY: Material entering stock
        - EXIT: Material leaving stock
        - TRANSFER: Material moving between locations
        - RESERVATION: Reserve material for project
        - EXPEDITION: Ship material to field

        Wraps various tools from agents.estoque_control.tools
        """
        try:
            movement_type_upper = movement_type.upper() if movement_type else "ENTRY"

            # Route to appropriate tool based on movement type
            if movement_type_upper == "TRANSFER":
                from agents.estoque_control.tools.transfer import create_transfer_tool

                result = await create_transfer_tool(
                    asset_id=asset_id,
                    part_number=part_number,
                    quantity=quantity,
                    from_location=from_location,
                    to_location=to_location,
                    reference=reference,
                    notes=notes,
                    user_id=user_id,
                    session_id=session_id,
                )

            elif movement_type_upper == "RESERVATION":
                from agents.estoque_control.tools.reservation import create_reservation_tool

                result = await create_reservation_tool(
                    asset_id=asset_id,
                    part_number=part_number,
                    quantity=quantity,
                    project_id=project_id,
                    location=from_location,
                    reference=reference,
                    notes=notes,
                    user_id=user_id,
                    session_id=session_id,
                )

            elif movement_type_upper == "EXPEDITION":
                from agents.estoque_control.tools.expedition import process_expedition_tool

                result = await process_expedition_tool(
                    asset_id=asset_id,
                    part_number=part_number,
                    quantity=quantity,
                    from_location=from_location,
                    to_location=to_location,
                    project_id=project_id,
                    reference=reference,
                    notes=notes,
                    user_id=user_id,
                    session_id=session_id,
                )

            elif movement_type_upper == "RETURN":
                from agents.estoque_control.tools.return_ops import process_return_tool

                result = await process_return_tool(
                    asset_id=asset_id,
                    part_number=part_number,
                    quantity=quantity,
                    from_location=from_location,
                    to_location=to_location,
                    reference=reference,
                    notes=notes,
                    user_id=user_id,
                    session_id=session_id,
                )

            else:
                # Default: Generic movement (ENTRY or EXIT)
                # Use direct database operation
                from tools.db_client import DBClient

                db = DBClient()

                movement_data = {
                    "movement_type": movement_type_upper,
                    "asset_id": asset_id,
                    "part_number": part_number,
                    "quantity": quantity,
                    "from_location_id": from_location,
                    "to_location_id": to_location,
                    "project_id": project_id,
                    "reference": reference,
                    "notes": notes,
                    "created_by": user_id,
                }

                result = await db.insert(
                    table="sga.movements",
                    data=movement_data,
                )

                result = {
                    "success": True,
                    "movement_id": result.get("id"),
                    "movement_type": movement_type_upper,
                }

            return result

        except ImportError as e:
            # Tool not implemented yet - return placeholder
            logger.warning(f"[{self.agent_name}] Tool not available: {e}")
            return {
                "success": False,
                "error": f"Movement type {movement_type} not fully implemented",
                "placeholder": True,
            }

        except Exception as e:
            logger.error(f"[{self.agent_name}] create_movement failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def query_balance(
        self,
        part_number: str = None,
        location_id: str = None,
        project_id: str = None,
        asset_id: str = None,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Query stock balance.

        Wraps agents.estoque_control.tools.query.query_balance_tool
        """
        try:
            from agents.estoque_control.tools.query import query_balance_tool

            result = await query_balance_tool(
                part_number=part_number,
                location_id=location_id,
                project_id=project_id,
                asset_id=asset_id,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] query_balance failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "balance": 0,
            }

    async def query_asset_location(
        self,
        asset_id: str,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Query asset current location.

        Wraps agents.estoque_control.tools.query.query_asset_location_tool
        """
        try:
            from agents.estoque_control.tools.query import query_asset_location_tool

            result = await query_asset_location_tool(
                asset_id=asset_id,
                session_id=session_id,
            )

            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] query_asset_location failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "asset_id": asset_id,
            }


# Export for import compatibility
__all__ = ["EstoqueControlAgent"]
