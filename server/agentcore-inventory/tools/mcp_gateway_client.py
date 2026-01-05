"""
MCP Gateway Client for AgentCore Communication.

This client handles communication with AgentCore Gateway using the MCP
(Model Context Protocol) library. Based on AWS documentation:
- gateway-agent-integration.html
- gateway-using-mcp-call.html
- gateway-using-mcp-list.html

Architecture:
    Agent → MCPGatewayClient → AgentCore Gateway → Lambda MCP Target

Key Features:
- Uses mcp.client.streamable_http for proper JSON-RPC 2.0 handling
- Supports tool discovery via list_tools()
- Supports tool invocation via call_tool()
- Handles JWT authentication with Bearer token
- Caches tool list for performance

Author: Faiston NEXO Team
Date: January 2026
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MCPGatewayClient:
    """
    Client for invoking tools via AgentCore Gateway using MCP protocol.

    This follows the official AWS pattern from gateway-agent-integration.html
    using mcp.client.streamable_http for proper protocol handling.

    Example usage:
        ```python
        client = MCPGatewayClient(
            gateway_url="https://{id}.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp",
            access_token_provider=lambda: get_jwt_token()
        )

        async with client.connect() as connected_client:
            tools = await connected_client.list_tools()
            result = await connected_client.call_tool(
                "SGAPostgresTools__sga_get_balance",
                {"part_number": "PN-001"}
            )
        ```

    Attributes:
        _gateway_url: Full MCP endpoint URL for AgentCore Gateway
        _get_access_token: Callable that returns current JWT access token
        _session: Active MCP ClientSession (set during connect())
        _tools_cache: Cached list of available tools
    """

    def __init__(
        self,
        gateway_url: str,
        access_token_provider: Callable[[], str]
    ):
        """
        Initialize MCP Gateway Client.

        Args:
            gateway_url: Gateway MCP endpoint URL
                Format: https://{gateway_id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp
            access_token_provider: Callable that returns current JWT access token
                This is called each time a connection is established to ensure fresh tokens
        """
        self._gateway_url = gateway_url
        self._get_access_token = access_token_provider
        self._session = None
        self._tools_cache: Optional[List[Dict]] = None

    @property
    def gateway_url(self) -> str:
        """Get the configured Gateway URL."""
        return self._gateway_url

    @property
    def is_connected(self) -> bool:
        """Check if client has an active session."""
        return self._session is not None

    @asynccontextmanager
    async def connect(self):
        """
        Establish MCP connection to Gateway.

        This context manager handles the full connection lifecycle:
        1. Gets fresh JWT token from provider
        2. Establishes streamable HTTP connection
        3. Initializes MCP session
        4. Yields connected client for use
        5. Cleans up on exit

        Per AWS docs, use streamablehttp_client for MCP communication.

        Yields:
            self: Connected MCPGatewayClient instance

        Raises:
            ImportError: If mcp package is not installed
            ConnectionError: If Gateway connection fails
        """
        # Lazy import to avoid cold start penalty when not using MCP
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError as e:
            logger.error("MCP package not installed. Install with: pip install mcp")
            raise ImportError(
                "MCP package required for Gateway communication. "
                "Install with: pip install mcp"
            ) from e

        # Get fresh access token
        access_token = self._get_access_token()
        if not access_token:
            raise ValueError("Access token provider returned empty token")

        headers = {"Authorization": f"Bearer {access_token}"}

        logger.info(f"Connecting to AgentCore Gateway: {self._gateway_url}")

        try:
            async with streamablehttp_client(
                url=self._gateway_url,
                headers=headers
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    self._session = session
                    logger.info("MCP session initialized successfully")
                    yield self
                    self._session = None
        except Exception as e:
            logger.error(f"Failed to connect to Gateway: {e}")
            self._session = None
            raise

    async def list_tools(self, use_cache: bool = True) -> List[Dict]:
        """
        List all available tools from Gateway.

        Per AWS docs (gateway-using-mcp-list.html), this method supports
        pagination for large tool sets. All pages are fetched and combined.

        Args:
            use_cache: If True, returns cached tools if available

        Returns:
            List of tool definitions with name, description, and input_schema

        Raises:
            RuntimeError: If called outside connect() context
        """
        if not self._session:
            raise RuntimeError("Must be called within connect() context manager")

        # Return cached tools if available
        if use_cache and self._tools_cache is not None:
            return self._tools_cache

        tools = []
        cursor = None  # None means first page

        while True:
            response = await self._session.list_tools(cursor)
            tools.extend(response.tools)

            # Check for more pages
            if hasattr(response, 'nextCursor') and response.nextCursor:
                cursor = response.nextCursor
            else:
                break

        # Cache for subsequent calls
        self._tools_cache = tools
        logger.info(f"Discovered {len(tools)} tools from Gateway")

        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke a tool via Gateway.

        Per AWS docs (gateway-using-mcp-call.html):
        - Method: tools/call (JSON-RPC 2.0)
        - Tool name format: {TargetName}__{tool_name}
        - Response contains content array with results

        Args:
            tool_name: Full tool name (e.g., "SGAPostgresTools__sga_get_balance")
            arguments: Tool arguments as dictionary

        Returns:
            Tool execution result parsed from response content

        Raises:
            RuntimeError: If called outside connect() context
            Exception: If tool execution fails
        """
        if not self._session:
            raise RuntimeError("Must be called within connect() context manager")

        logger.debug(f"Calling tool: {tool_name} with args: {arguments}")

        try:
            response = await self._session.call_tool(
                name=tool_name,
                arguments=arguments
            )

            # Parse response content
            # MCP response has content array with type and text/data
            if hasattr(response, 'content') and response.content:
                for content_item in response.content:
                    if hasattr(content_item, 'text'):
                        # Parse JSON text response
                        import json
                        return json.loads(content_item.text)
                    elif hasattr(content_item, 'data'):
                        return content_item.data

            # Return raw response if no parseable content
            return {"raw_response": str(response)}

        except Exception as e:
            logger.error(f"Tool call failed: {tool_name} - {e}")
            raise

    async def search_tools(self, query: str) -> List[Dict]:
        """
        Semantic search for tools (if enabled on Gateway).

        Per AWS docs (gateway-using-mcp-semantic-search.html):
        - Uses special tool: x_amz_bedrock_agentcore_search
        - Returns relevant tools based on natural language query

        Args:
            query: Natural language description of desired functionality

        Returns:
            List of matching tool definitions

        Raises:
            RuntimeError: If called outside connect() context
        """
        if not self._session:
            raise RuntimeError("Must be called within connect() context manager")

        logger.info(f"Searching tools with query: {query}")

        try:
            response = await self.call_tool(
                tool_name="x_amz_bedrock_agentcore_search",
                arguments={"query": query}
            )
            return response.get("tools", [])
        except Exception as e:
            logger.warning(f"Semantic search failed (may not be enabled): {e}")
            # Fall back to listing all tools
            return await self.list_tools()

    def clear_cache(self) -> None:
        """Clear the cached tools list."""
        self._tools_cache = None


class MCPGatewayClientFactory:
    """
    Factory for creating MCPGatewayClient instances.

    This factory handles configuration from environment variables
    and provides a consistent way to create clients across agents.

    Environment Variables:
        AGENTCORE_GATEWAY_URL: Full MCP endpoint URL
        AGENTCORE_GATEWAY_ID: Gateway ID (alternative to full URL)
        AWS_REGION: AWS region for URL construction
    """

    @staticmethod
    def create_from_env(
        access_token_provider: Callable[[], str]
    ) -> MCPGatewayClient:
        """
        Create MCPGatewayClient from environment variables.

        Args:
            access_token_provider: Callable that returns JWT access token

        Returns:
            Configured MCPGatewayClient instance

        Raises:
            ValueError: If required environment variables are missing
        """
        # Try full URL first
        gateway_url = os.environ.get("AGENTCORE_GATEWAY_URL")

        if not gateway_url:
            # Construct from ID and region
            gateway_id = os.environ.get("AGENTCORE_GATEWAY_ID")
            region = os.environ.get("AWS_REGION", "us-east-2")

            if not gateway_id:
                raise ValueError(
                    "Either AGENTCORE_GATEWAY_URL or AGENTCORE_GATEWAY_ID "
                    "environment variable must be set"
                )

            gateway_url = (
                f"https://{gateway_id}.gateway.bedrock-agentcore."
                f"{region}.amazonaws.com/mcp"
            )

        return MCPGatewayClient(
            gateway_url=gateway_url,
            access_token_provider=access_token_provider
        )
