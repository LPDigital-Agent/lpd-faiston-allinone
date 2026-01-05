"""
PostgreSQL MCP Tools Lambda Handler.

This Lambda function handles tool invocations from AgentCore Gateway.
Per AWS documentation (gateway-agent-integration.html), the Gateway sends
tool calls with the format: {TargetName}__{ToolName}

Architecture:
    AgentCore Gateway -> Lambda (this) -> RDS Proxy -> Aurora PostgreSQL

Tool Naming Convention:
    Gateway sends: SGAPostgresTools__sga_list_inventory
    Handler strips prefix and routes to appropriate function.

Author: Faiston NEXO Team
Date: January 2026
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, date

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Target prefix for tool naming
TARGET_PREFIX = "SGAPostgresTools"


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for AgentCore Gateway tool invocation.

    Args:
        event: Gateway tool call event with 'name' and 'arguments'
        context: Lambda context

    Returns:
        Tool execution result or error
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract tool name and arguments
        tool_name = event.get("name", "")
        arguments = event.get("arguments", {})

        # Strip target prefix (SGAPostgresTools__)
        if "__" in tool_name:
            actual_tool = tool_name.split("__")[-1]
        else:
            actual_tool = tool_name

        logger.info(f"Executing tool: {actual_tool} with args: {arguments}")

        # Route to appropriate handler
        handlers = {
            "sga_list_inventory": handle_list_inventory,
            "sga_get_balance": handle_get_balance,
            "sga_search_assets": handle_search_assets,
            "sga_get_asset_timeline": handle_get_asset_timeline,
            "sga_get_movements": handle_get_movements,
            "sga_get_pending_tasks": handle_get_pending_tasks,
            "sga_create_movement": handle_create_movement,
            "sga_reconcile_sap": handle_reconcile_sap,
        }

        if actual_tool not in handlers:
            logger.error(f"Unknown tool: {actual_tool}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"error": f"Unknown tool: {actual_tool}"})
                    }
                ],
                "isError": True
            }

        # Execute the tool handler
        result = handlers[actual_tool](arguments)

        logger.info(f"Tool result: {result}")

        # Return MCP-formatted response
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, default=json_serializer)
                }
            ],
            "isError": False
        }

    except Exception as e:
        logger.exception(f"Error executing tool: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": str(e)})
                }
            ],
            "isError": True
        }


def json_serializer(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# =============================================================================
# Tool Handlers
# =============================================================================

def handle_list_inventory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    List assets and balances with optional filters.

    Args:
        location_id: Filter by location
        project_id: Filter by project
        part_number: Filter by part number
        status: Filter by asset status
        limit: Max results (default 100)
        offset: Pagination offset
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    filters = {
        "location_id": arguments.get("location_id"),
        "project_id": arguments.get("project_id"),
        "part_number": arguments.get("part_number"),
        "status": arguments.get("status"),
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    limit = arguments.get("limit", 100)
    offset = arguments.get("offset", 0)

    return client.list_inventory(filters=filters, limit=limit, offset=offset)


def handle_get_balance(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get stock balance for a part number.

    Args:
        part_number: Part number to query (required)
        location_id: Filter by location (optional)
        project_id: Filter by project (optional)
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    part_number = arguments.get("part_number")
    if not part_number:
        return {"error": "part_number is required"}

    return client.get_balance(
        part_number=part_number,
        location_id=arguments.get("location_id"),
        project_id=arguments.get("project_id")
    )


def handle_search_assets(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search assets by serial number, part number, or description.

    Args:
        query: Search term (required)
        search_type: Type of search (serial, part_number, description, all)
        limit: Max results
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    query = arguments.get("query")
    if not query:
        return {"error": "query is required"}

    return client.search_assets(
        query=query,
        search_type=arguments.get("search_type", "all"),
        limit=arguments.get("limit", 50)
    )


def handle_get_asset_timeline(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get complete history of an asset (event sourcing).

    Args:
        identifier: Asset ID or serial number (required)
        identifier_type: Type of identifier (asset_id, serial_number)
        limit: Max results
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    identifier = arguments.get("identifier")
    if not identifier:
        return {"error": "identifier is required"}

    return client.get_asset_timeline(
        identifier=identifier,
        identifier_type=arguments.get("identifier_type", "serial_number"),
        limit=arguments.get("limit", 100)
    )


def handle_get_movements(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    List movements with filters.

    Args:
        start_date: Start date filter
        end_date: End date filter
        movement_type: Type of movement
        project_id: Filter by project
        location_id: Filter by location
        limit: Max results
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    filters = {
        "start_date": arguments.get("start_date"),
        "end_date": arguments.get("end_date"),
        "movement_type": arguments.get("movement_type"),
        "project_id": arguments.get("project_id"),
        "location_id": arguments.get("location_id"),
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    return client.get_movements(
        filters=filters,
        limit=arguments.get("limit", 100)
    )


def handle_get_pending_tasks(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    List pending approval tasks (HIL).

    Args:
        task_type: Type of task
        priority: Task priority
        assignee_id: Filter by assignee
        limit: Max results
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    filters = {
        "task_type": arguments.get("task_type"),
        "priority": arguments.get("priority"),
        "assignee_id": arguments.get("assignee_id"),
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    return client.get_pending_tasks(
        filters=filters,
        limit=arguments.get("limit", 50)
    )


def handle_create_movement(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new inventory movement.

    Args:
        movement_type: Type of movement (required)
        part_number: Part number (required)
        quantity: Quantity (required)
        source_location_id: Source location (for exit/transfer)
        destination_location_id: Destination location (for entry/transfer)
        project_id: Project
        serial_numbers: List of serial numbers
        nf_number: NF number
        nf_date: NF date
        reason: Reason for movement
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    # Validate required fields
    required = ["movement_type", "part_number", "quantity"]
    for field in required:
        if field not in arguments:
            return {"error": f"{field} is required"}

    return client.create_movement(
        movement_type=arguments["movement_type"],
        part_number=arguments["part_number"],
        quantity=arguments["quantity"],
        source_location_id=arguments.get("source_location_id"),
        destination_location_id=arguments.get("destination_location_id"),
        project_id=arguments.get("project_id"),
        serial_numbers=arguments.get("serial_numbers", []),
        nf_number=arguments.get("nf_number"),
        nf_date=arguments.get("nf_date"),
        reason=arguments.get("reason")
    )


def handle_reconcile_sap(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare SGA inventory with SAP export data.

    Args:
        sap_data: List of SAP items to compare (required)
        include_serials: Include serial number comparison
    """
    from postgres_client import SGAPostgresClient

    client = SGAPostgresClient()

    sap_data = arguments.get("sap_data")
    if not sap_data:
        return {"error": "sap_data is required"}

    return client.reconcile_with_sap(
        sap_data=sap_data,
        include_serials=arguments.get("include_serials", False)
    )
