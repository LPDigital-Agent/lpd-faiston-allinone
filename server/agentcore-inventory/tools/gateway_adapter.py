"""
Gateway PostgreSQL Adapter for SGA Inventory.

Implements DatabaseAdapter interface by routing database operations
through AgentCore Gateway MCP protocol to Lambda PostgreSQL tools.

Architecture:
    Agent → GatewayPostgresAdapter → MCPGatewayClient → AgentCore Gateway → Lambda → Aurora PostgreSQL

Tool Naming Convention (per AWS docs):
    Format: {TargetName}__{ToolName}
    Example: SGAPostgresTools__sga_get_balance

Author: Faiston NEXO Team
Date: January 2026
"""

import logging
from typing import Any, Dict, List, Optional

from tools.database_adapter import (
    DatabaseAdapter,
    InventoryFilters,
    MovementFilters,
    MovementData,
    AssetStatus,
    MovementType,
)
from tools.mcp_gateway_client import MCPGatewayClient

logger = logging.getLogger(__name__)


class GatewayPostgresAdapter(DatabaseAdapter):
    """
    Adapter that routes database calls through AgentCore Gateway MCP.

    This adapter translates DatabaseAdapter method calls into MCP tool
    invocations via the Gateway. It handles:
    - Tool name prefixing with target name
    - Argument serialization
    - Response parsing
    - Error handling and logging

    Attributes:
        TARGET_PREFIX: MCP target name for PostgreSQL tools
        _client: MCPGatewayClient instance for Gateway communication
    """

    TARGET_PREFIX = "SGAPostgresTools"

    def __init__(self, mcp_client: MCPGatewayClient):
        """
        Initialize Gateway PostgreSQL Adapter.

        Args:
            mcp_client: Configured MCPGatewayClient for Gateway communication
        """
        self._client = mcp_client

    def _tool_name(self, tool: str) -> str:
        """
        Build full tool name with target prefix.

        Per AWS docs, Gateway routes to targets using the naming convention:
        {TargetName}__{ToolName}

        Args:
            tool: Base tool name (e.g., "sga_get_balance")

        Returns:
            Full tool name (e.g., "SGAPostgresTools__sga_get_balance")
        """
        return f"{self.TARGET_PREFIX}__{tool}"

    def _clean_none_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove None values from dictionary for cleaner MCP calls.

        Args:
            data: Dictionary potentially containing None values

        Returns:
            Dictionary with None values removed
        """
        return {k: v for k, v in data.items() if v is not None}

    async def list_inventory(
        self,
        filters: Optional[InventoryFilters] = None
    ) -> Dict[str, Any]:
        """
        List assets and balances with optional filters.

        Calls: SGAPostgresTools__sga_list_inventory
        """
        arguments = {}
        if filters:
            arguments = self._clean_none_values({
                "location_id": filters.location_id,
                "project_id": filters.project_id,
                "part_number": filters.part_number,
                "status": filters.status.value if filters.status else None,
                "limit": filters.limit,
                "offset": filters.offset,
            })

        logger.debug(f"list_inventory with filters: {arguments}")

        return await self._client.call_tool(
            tool_name=self._tool_name("sga_list_inventory"),
            arguments=arguments
        )

    async def get_balance(
        self,
        part_number: str,
        location_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get stock balance for a part number.

        Calls: SGAPostgresTools__sga_get_balance
        """
        arguments = self._clean_none_values({
            "part_number": part_number,
            "location_id": location_id,
            "project_id": project_id,
        })

        logger.debug(f"get_balance for: {part_number}")

        return await self._client.call_tool(
            tool_name=self._tool_name("sga_get_balance"),
            arguments=arguments
        )

    async def search_assets(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search assets by serial number, part number, or description.

        Calls: SGAPostgresTools__sga_search_assets
        """
        arguments = {
            "query": query,
            "search_type": search_type,
            "limit": limit,
        }

        logger.debug(f"search_assets: query='{query}', type={search_type}")

        result = await self._client.call_tool(
            tool_name=self._tool_name("sga_search_assets"),
            arguments=arguments
        )

        # Return items list from result
        return result.get("items", []) if isinstance(result, dict) else result

    async def get_asset_timeline(
        self,
        identifier: str,
        identifier_type: str = "serial_number",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get complete history of an asset (event sourcing).

        Calls: SGAPostgresTools__sga_get_asset_timeline
        """
        arguments = {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "limit": limit,
        }

        logger.debug(f"get_asset_timeline: {identifier_type}={identifier}")

        result = await self._client.call_tool(
            tool_name=self._tool_name("sga_get_asset_timeline"),
            arguments=arguments
        )

        return result.get("events", []) if isinstance(result, dict) else result

    async def get_movements(
        self,
        filters: Optional[MovementFilters] = None
    ) -> List[Dict[str, Any]]:
        """
        List movements with filters.

        Calls: SGAPostgresTools__sga_get_movements
        """
        arguments = {}
        if filters:
            arguments = self._clean_none_values({
                "start_date": filters.start_date,
                "end_date": filters.end_date,
                "movement_type": filters.movement_type.value if filters.movement_type else None,
                "project_id": filters.project_id,
                "location_id": filters.location_id,
                "limit": filters.limit,
            })

        logger.debug(f"get_movements with filters: {arguments}")

        result = await self._client.call_tool(
            tool_name=self._tool_name("sga_get_movements"),
            arguments=arguments
        )

        return result.get("movements", []) if isinstance(result, dict) else result

    async def get_pending_tasks(
        self,
        task_type: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List pending approval tasks (Human-in-the-Loop).

        Calls: SGAPostgresTools__sga_get_pending_tasks
        """
        arguments = self._clean_none_values({
            "task_type": task_type,
            "priority": priority,
            "assignee_id": assignee_id,
            "limit": limit,
        })

        logger.debug(f"get_pending_tasks: {arguments}")

        result = await self._client.call_tool(
            tool_name=self._tool_name("sga_get_pending_tasks"),
            arguments=arguments
        )

        return result.get("tasks", []) if isinstance(result, dict) else result

    async def create_movement(
        self,
        movement_data: MovementData
    ) -> Dict[str, Any]:
        """
        Create a new inventory movement.

        Calls: SGAPostgresTools__sga_create_movement
        """
        arguments = self._clean_none_values({
            "movement_type": movement_data.movement_type.value,
            "part_number": movement_data.part_number,
            "quantity": movement_data.quantity,
            "source_location_id": movement_data.source_location_id,
            "destination_location_id": movement_data.destination_location_id,
            "project_id": movement_data.project_id,
            "serial_numbers": movement_data.serial_numbers,
            "nf_number": movement_data.nf_number,
            "nf_date": movement_data.nf_date,
            "reason": movement_data.reason,
        })

        logger.info(
            f"create_movement: type={movement_data.movement_type}, "
            f"part={movement_data.part_number}, qty={movement_data.quantity}"
        )

        return await self._client.call_tool(
            tool_name=self._tool_name("sga_create_movement"),
            arguments=arguments
        )

    async def reconcile_with_sap(
        self,
        sap_data: List[Dict[str, Any]],
        include_serials: bool = False
    ) -> Dict[str, Any]:
        """
        Compare SGA inventory with SAP export data.

        Calls: SGAPostgresTools__sga_reconcile_sap
        """
        arguments = {
            "sap_data": sap_data,
            "include_serials": include_serials,
        }

        logger.info(f"reconcile_with_sap: {len(sap_data)} items")

        return await self._client.call_tool(
            tool_name=self._tool_name("sga_reconcile_sap"),
            arguments=arguments
        )


class GatewayAdapterFactory:
    """
    Factory for creating GatewayPostgresAdapter instances.

    Handles the setup of MCPGatewayClient and adapter creation,
    abstracting the complexity from agent code.
    """

    @staticmethod
    async def create_with_context(
        gateway_url: str,
        access_token: str
    ) -> GatewayPostgresAdapter:
        """
        Create adapter with pre-configured context.

        This is a convenience method for creating an adapter when you
        already have the gateway URL and access token available.

        Args:
            gateway_url: Full Gateway MCP endpoint URL
            access_token: JWT access token for authentication

        Returns:
            Configured GatewayPostgresAdapter
        """
        from tools.mcp_gateway_client import MCPGatewayClient

        client = MCPGatewayClient(
            gateway_url=gateway_url,
            access_token_provider=lambda: access_token
        )

        return GatewayPostgresAdapter(client)
