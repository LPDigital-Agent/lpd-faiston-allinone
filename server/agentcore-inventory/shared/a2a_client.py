# =============================================================================
# A2A Client - Agent-to-Agent Communication
# =============================================================================
# Standardized client for A2A protocol (JSON-RPC 2.0) communication between
# AgentCore Runtimes.
#
# Usage:
#   from shared.a2a_client import A2AClient
#   client = A2AClient()
#   result = await client.invoke_agent("learning", {
#       "action": "retrieve_prior_knowledge",
#       "filename_pattern": "EXPEDIÇÃO_*.csv"
#   })
#
# Architecture:
# - JSON-RPC 2.0 over HTTP (port 9000)
# - Agent discovery via SSM Parameter Store
# - AgentCore Identity for authentication
# - X-Ray tracing for distributed observability
#
# Reference:
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a-protocol-contract.html
# =============================================================================

import os
import json
import uuid
import asyncio
import random
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)

# Lazy imports for cold start optimization
_httpx = None
_boto3 = None

# =============================================================================
# Retry Configuration (AWS Best Practices)
# =============================================================================

# Retryable HTTP status codes
RETRYABLE_STATUS_CODES: Set[int] = {
    429,  # Too Many Requests (throttling)
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}

# Retry configuration
MAX_RETRIES = 5
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 16.0  # seconds
JITTER_RANGE = 0.5  # ±50% jitter


def _get_httpx():
    """Lazy load httpx."""
    global _httpx
    if _httpx is None:
        import httpx
        _httpx = httpx
    return _httpx


def _get_boto3():
    """Lazy load boto3."""
    global _boto3
    if _boto3 is None:
        import boto3
        _boto3 = boto3
    return _boto3


@dataclass
class A2AMessage:
    """
    A2A Protocol message structure.

    Follows the A2A Protocol contract:
    https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a-protocol-contract.html
    """
    role: str = "user"
    text: str = ""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class A2AResponse:
    """
    A2A Protocol response structure.

    Attributes:
        success: Whether the call succeeded
        response: Response text from the agent
        agent_id: ID of the agent that responded
        message_id: ID of the request message
        error: Error message if failed
        raw_response: Full JSON-RPC response
    """
    success: bool
    response: str
    agent_id: str
    message_id: str
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class A2AClient:
    """
    Client for A2A (Agent-to-Agent) protocol communication.

    Handles:
    - Agent discovery via SSM Parameter Store
    - JSON-RPC 2.0 message formatting
    - SigV4 authentication for AgentCore Runtime
    - X-Ray tracing integration

    Example:
        client = A2AClient()

        # Simple invocation
        result = await client.invoke_agent("learning", {
            "action": "retrieve_prior_knowledge",
            "filename": "EXPEDIÇÃO_JAN_2026.csv"
        })

        # With session context
        result = await client.invoke_agent(
            "validation",
            {"action": "validate_schema", "columns": ["PN", "QTD"]},
            session_id="session-123"
        )
    """

    # SSM parameter path for agent registry
    REGISTRY_PARAM = "/{project}/sga/agents/registry"

    def __init__(self, project_name: Optional[str] = None):
        """
        Initialize A2A client.

        Args:
            project_name: Project name for SSM parameters (default: from env)
        """
        self.project_name = project_name or os.environ.get("PROJECT_NAME", "faiston-one")
        self.region = os.environ.get("AWS_REGION", "us-east-2")
        self._agent_registry: Optional[Dict] = None
        self._ssm_client = None

    @property
    def ssm_client(self):
        """Lazy-load SSM client."""
        if self._ssm_client is None:
            boto3 = _get_boto3()
            self._ssm_client = boto3.client("ssm", region_name=self.region)
        return self._ssm_client

    async def get_agent_registry(self) -> Dict[str, Dict]:
        """
        Get agent registry from SSM Parameter Store.

        Returns:
            Dict mapping agent_id -> agent config (name, url, skills, etc.)
        """
        if self._agent_registry is not None:
            return self._agent_registry

        try:
            param_name = self.REGISTRY_PARAM.format(project=self.project_name)
            response = self.ssm_client.get_parameter(Name=param_name)
            self._agent_registry = json.loads(response["Parameter"]["Value"])
            return self._agent_registry
        except Exception as e:
            print(f"[A2A] Failed to load agent registry: {e}")
            return {}

    async def get_agent_url(self, agent_id: str) -> Optional[str]:
        """
        Get invocation URL for an agent.

        Args:
            agent_id: Agent identifier (e.g., "learning", "validation")

        Returns:
            Agent invocation URL or None if not found
        """
        # Check environment variable first (for local development)
        env_var = f"AGENT_URL_{agent_id.upper()}"
        if env_var in os.environ:
            return os.environ[env_var]

        # Look up in registry
        registry = await self.get_agent_registry()
        agent_config = registry.get(agent_id)
        if agent_config:
            return agent_config.get("url")

        return None

    def _build_a2a_request(
        self,
        payload: Dict[str, Any],
        message_id: Optional[str] = None
    ) -> Dict:
        """
        Build JSON-RPC 2.0 request for A2A protocol.

        Args:
            payload: Payload to send to agent
            message_id: Optional message ID (generated if not provided)

        Returns:
            JSON-RPC 2.0 request dict
        """
        msg_id = message_id or str(uuid.uuid4())

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": json.dumps(payload)
                        }
                    ],
                    "messageId": msg_id
                }
            }
        }

    def _parse_a2a_response(
        self,
        response: Dict,
        agent_id: str,
        message_id: str
    ) -> A2AResponse:
        """
        Parse JSON-RPC 2.0 response from A2A call.

        Args:
            response: Raw JSON-RPC response
            agent_id: ID of the agent that was called
            message_id: ID of the request message

        Returns:
            Parsed A2AResponse
        """
        # Check for JSON-RPC error
        if "error" in response:
            return A2AResponse(
                success=False,
                response="",
                agent_id=agent_id,
                message_id=message_id,
                error=response["error"].get("message", "Unknown error"),
                raw_response=response,
            )

        # Extract response text from result
        result = response.get("result", {})
        message = result.get("message", {})
        parts = message.get("parts", [])

        response_text = ""
        for part in parts:
            if part.get("kind") == "text":
                response_text += part.get("text", "")

        return A2AResponse(
            success=True,
            response=response_text,
            agent_id=agent_id,
            message_id=message_id,
            raw_response=response,
        )

    async def invoke_agent(
        self,
        agent_id: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: float = 30.0,
    ) -> A2AResponse:
        """
        Invoke another agent via A2A protocol.

        This is the main method for cross-agent communication.

        Args:
            agent_id: ID of the agent to invoke (e.g., "learning", "validation")
            payload: Payload to send (will be JSON-serialized)
            session_id: Optional session ID for context continuity
            timeout: Request timeout in seconds

        Returns:
            A2AResponse with success status and response text

        Example:
            result = await client.invoke_agent("learning", {
                "action": "retrieve_prior_knowledge",
                "filename_pattern": "EXPEDIÇÃO_*.csv",
                "columns": ["PN", "QTD", "DESCRICAO"]
            })

            if result.success:
                prior_knowledge = json.loads(result.response)
        """
        # Import audit emitter for event emission
        from shared.audit_emitter import AgentAuditEmitter

        # Get current agent ID from environment
        current_agent = os.environ.get("AGENT_ID", "unknown")
        audit = AgentAuditEmitter(current_agent)

        # Get target agent URL
        agent_url = await self.get_agent_url(agent_id)
        if not agent_url:
            return A2AResponse(
                success=False,
                response="",
                agent_id=agent_id,
                message_id="",
                error=f"Agent '{agent_id}' not found in registry",
            )

        # Emit delegation event
        audit.delegating(
            target_agent=agent_id,
            message=f"Delegando para {agent_id}...",
            session_id=session_id,
        )

        # Build A2A request
        message_id = str(uuid.uuid4())
        a2a_request = self._build_a2a_request(payload, message_id)

        # Build headers
        headers = {
            "Content-Type": "application/json",
        }

        # Add session ID if provided
        if session_id:
            headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = session_id

        try:
            httpx = _get_httpx()

            # =================================================================
            # Exponential Backoff with Jitter (AWS Best Practices)
            # =================================================================
            last_exception = None

            for attempt in range(MAX_RETRIES):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            agent_url,
                            json=a2a_request,
                            headers=headers,
                        )

                        # Check if retryable status code
                        if response.status_code in RETRYABLE_STATUS_CODES:
                            # Calculate backoff delay with jitter
                            delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                            jitter = delay * JITTER_RANGE * (2 * random.random() - 1)
                            delay = delay + jitter

                            # Check Retry-After header
                            retry_after = response.headers.get("Retry-After")
                            if retry_after:
                                try:
                                    delay = max(delay, float(retry_after))
                                except ValueError:
                                    pass

                            logger.warning(
                                f"[A2A] {response.status_code} from {agent_id}, "
                                f"retry {attempt + 1}/{MAX_RETRIES} after {delay:.2f}s"
                            )
                            await asyncio.sleep(delay)
                            continue

                        response.raise_for_status()
                        response_data = response.json()

                        return self._parse_a2a_response(response_data, agent_id, message_id)

                except httpx.TimeoutException as e:
                    last_exception = e
                    if attempt < MAX_RETRIES - 1:
                        delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                        jitter = delay * JITTER_RANGE * (2 * random.random() - 1)
                        delay = delay + jitter
                        logger.warning(
                            f"[A2A] Timeout calling {agent_id}, "
                            f"retry {attempt + 1}/{MAX_RETRIES} after {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise

                except httpx.HTTPStatusError as e:
                    # Non-retryable HTTP errors
                    if e.response.status_code not in RETRYABLE_STATUS_CODES:
                        raise
                    last_exception = e

            # Max retries exceeded
            if last_exception:
                raise last_exception
            raise Exception(f"Max retries ({MAX_RETRIES}) exceeded for {agent_id}")

        except Exception as e:
            audit.error(
                message=f"Erro ao chamar {agent_id}",
                session_id=session_id,
                error=str(e),
            )
            return A2AResponse(
                success=False,
                response="",
                agent_id=agent_id,
                message_id=message_id,
                error=str(e),
            )

    async def invoke_with_streaming(
        self,
        agent_id: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Invoke another agent with streaming response.

        Yields response chunks as they arrive.

        Args:
            agent_id: ID of the agent to invoke
            payload: Payload to send
            session_id: Optional session ID
            timeout: Request timeout in seconds

        Yields:
            Response text chunks
        """
        # Get target agent URL
        agent_url = await self.get_agent_url(agent_id)
        if not agent_url:
            yield f"Error: Agent '{agent_id}' not found"
            return

        # Build A2A request with streaming flag
        message_id = str(uuid.uuid4())
        a2a_request = self._build_a2a_request(payload, message_id)

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        if session_id:
            headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = session_id

        try:
            httpx = _get_httpx()

            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    agent_url,
                    json=a2a_request,
                    headers=headers,
                ) as response:
                    async for chunk in response.aiter_text():
                        yield chunk

        except Exception as e:
            yield f"Error: {str(e)}"


# =============================================================================
# Convenience Functions
# =============================================================================

async def delegate_to_learning(
    payload: Dict[str, Any],
    session_id: Optional[str] = None
) -> A2AResponse:
    """
    Convenience function to delegate to LearningAgent.

    Args:
        payload: Payload with action and parameters
        session_id: Optional session ID

    Returns:
        A2AResponse from LearningAgent
    """
    client = A2AClient()
    return await client.invoke_agent("learning", payload, session_id)


async def delegate_to_validation(
    payload: Dict[str, Any],
    session_id: Optional[str] = None
) -> A2AResponse:
    """
    Convenience function to delegate to ValidationAgent.

    Args:
        payload: Payload with action and parameters
        session_id: Optional session ID

    Returns:
        A2AResponse from ValidationAgent
    """
    client = A2AClient()
    return await client.invoke_agent("validation", payload, session_id)


async def delegate_to_schema_evolution(
    payload: Dict[str, Any],
    session_id: Optional[str] = None
) -> A2AResponse:
    """
    Convenience function to delegate to SchemaEvolutionAgent.

    Args:
        payload: Payload with action and parameters
        session_id: Optional session ID

    Returns:
        A2AResponse from SchemaEvolutionAgent
    """
    client = A2AClient()
    return await client.invoke_agent("schema_evolution", payload, session_id)
