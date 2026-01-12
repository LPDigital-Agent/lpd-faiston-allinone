# =============================================================================
# A2A Client - Agent-to-Agent Communication (Strands A2AServer Compatible)
# =============================================================================
# Standardized client for A2A protocol (JSON-RPC 2.0) communication between
# AgentCore Runtimes using Strands A2AServer.
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
# - JSON-RPC 2.0 over HTTP (port 9000, path /)
# - Agent Card discovery at /.well-known/agent-card.json
# - Agent discovery via SSM Parameter Store
# - AgentCore Identity for authentication (SigV4)
# - X-Ray tracing for distributed observability
#
# Migration Note:
# - Migrated from BedrockAgentCoreApp (HTTP, port 8080, /invocations)
# - Now uses Strands A2AServer (A2A, port 9000, /)
#
# Reference:
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a-protocol-contract.html
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
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


@dataclass
class AgentCard:
    """
    A2A Protocol Agent Card structure.

    The Agent Card provides discovery information about an agent's capabilities.
    Served at /.well-known/agent-card.json per A2A specification.

    Reference: https://a2a-protocol.org/latest/specification/
    """
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocol_version: str = "0.1"
    capabilities: List[str] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    authentication: Dict[str, Any] = field(default_factory=dict)


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

    def _get_session(self):
        """Get boto3 session for credential management."""
        if not hasattr(self, '_boto3_session') or self._boto3_session is None:
            boto3 = _get_boto3()
            self._boto3_session = boto3.Session()
        return self._boto3_session

    def _get_credentials(self):
        """
        Get fresh AWS credentials.

        Uses boto3 Session which handles credential refresh automatically
        for temporary credentials (from IAM roles, instance profiles, etc.)
        """
        session = self._get_session()
        credentials = session.get_credentials()
        if credentials is None:
            raise ValueError(
                "No AWS credentials found. Ensure IAM role is configured "
                "or AWS credentials are available in environment."
            )
        return credentials.get_frozen_credentials()

    def _sign_request(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Sign HTTP request with AWS SigV4 for AgentCore Runtime.

        The InvokeAgentRuntime API requires SigV4 authentication.
        This follows the same pattern as mcp_gateway_client.py.

        Args:
            method: HTTP method (POST, GET, etc.)
            url: Full request URL
            payload: Request body as dictionary

        Returns:
            Dictionary of signed headers to include in request
        """
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        body = json.dumps(payload)

        # Create AWS request object
        request = AWSRequest(
            method=method,
            url=url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        # Sign with SigV4 for bedrock-agentcore service
        credentials = self._get_credentials()
        SigV4Auth(credentials, "bedrock-agentcore", self.region).add_auth(request)

        logger.debug(f"[A2A] Request signed for bedrock-agentcore")

        return dict(request.headers)

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

    async def get_agent_card(
        self,
        agent_id: str,
        timeout: float = 10.0
    ) -> Optional[AgentCard]:
        """
        Discover agent capabilities via Agent Card.

        Fetches the Agent Card from /.well-known/agent-card.json endpoint.
        The Agent Card provides discovery information about an agent's capabilities,
        skills, and authentication requirements.

        Args:
            agent_id: ID of the agent to discover
            timeout: Request timeout in seconds

        Returns:
            AgentCard with agent capabilities, or None if not available

        Example:
            card = await client.get_agent_card("learning")
            if card:
                print(f"Agent {card.name} has skills: {card.skills}")
        """
        agent_url = await self.get_agent_url(agent_id)
        if not agent_url:
            logger.warning(f"[A2A] Agent '{agent_id}' not found for card discovery")
            return None

        # Build Agent Card URL
        # For A2A protocol: base_url/.well-known/agent-card.json
        # Handle both trailing slash and no trailing slash cases
        base_url = agent_url.rstrip("/").split("?")[0]  # Remove query params and trailing slash
        agent_card_url = f"{base_url}/.well-known/agent-card.json"

        try:
            httpx = _get_httpx()

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(agent_card_url)

                if response.status_code == 404:
                    logger.info(f"[A2A] Agent Card not available for {agent_id}")
                    return None

                response.raise_for_status()
                card_data = response.json()

                return AgentCard(
                    name=card_data.get("name", agent_id),
                    description=card_data.get("description", ""),
                    url=card_data.get("url", agent_url),
                    version=card_data.get("version", "1.0.0"),
                    protocol_version=card_data.get("protocolVersion", "0.1"),
                    capabilities=card_data.get("capabilities", []),
                    skills=card_data.get("skills", []),
                    authentication=card_data.get("authentication", {}),
                )

        except Exception as e:
            logger.warning(f"[A2A] Failed to fetch Agent Card for {agent_id}: {e}")
            return None

    async def validate_agent_availability(
        self,
        agent_id: str,
        timeout: float = 10.0
    ) -> bool:
        """
        Check if an agent is available and responding.

        Uses Agent Card discovery to verify the agent is reachable.
        This is useful for health checks and pre-flight validation.

        Args:
            agent_id: ID of the agent to check
            timeout: Request timeout in seconds

        Returns:
            True if agent is available, False otherwise
        """
        card = await self.get_agent_card(agent_id, timeout)
        return card is not None

    def _normalize_url(self, url: str) -> str:
        """
        Normalize agent URL for AgentCore Runtime invocation.

        BUG-010 FIX: The correct path for invoking AgentCore A2A runtimes is
        /invocations/ (not /? or root path). The SSM parameters store URLs
        with /?qualifier=DEFAULT format, but the actual invocation API expects
        /invocations/ path.

        Reference: https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/a2a.md

        Args:
            url: Raw URL from registry (may have /?qualifier=DEFAULT suffix)

        Returns:
            Normalized URL with /invocations/ path for AgentCore API
        """
        # Remove ?qualifier=DEFAULT suffix if present (endpoint format, not invocation)
        if "?qualifier=" in url:
            url = url.split("?")[0]

        # Remove trailing slash for clean base URL
        url = url.rstrip("/")

        # Ensure URL ends with /invocations/ for AgentCore Runtime API
        # This is required for InvokeAgentRuntime API calls
        if not url.endswith("/invocations"):
            url = url + "/invocations/"
        elif not url.endswith("/"):
            url = url + "/"

        return url

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

        # Get target agent URL and normalize for A2A protocol
        agent_url = await self.get_agent_url(agent_id)
        if not agent_url:
            return A2AResponse(
                success=False,
                response="",
                agent_id=agent_id,
                message_id="",
                error=f"Agent '{agent_id}' not found in registry",
            )

        # Normalize URL for A2A protocol (handles legacy /invocations URLs)
        agent_url = self._normalize_url(agent_url)

        # Emit delegation event
        audit.delegating(
            target_agent=agent_id,
            message=f"Delegando para {agent_id}...",
            session_id=session_id,
        )

        # Build A2A request
        message_id = str(uuid.uuid4())
        a2a_request = self._build_a2a_request(payload, message_id)

        # Sign request with SigV4 (REQUIRED for InvokeAgentRuntime API)
        # FIX: Previous code used plain headers without SigV4 auth, causing 403 Forbidden
        headers = self._sign_request("POST", agent_url, a2a_request)

        # Add session ID if provided (after signing - not included in signature)
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
        # Get target agent URL and normalize for A2A protocol
        agent_url = await self.get_agent_url(agent_id)
        if not agent_url:
            yield f"Error: Agent '{agent_id}' not found"
            return

        # Normalize URL for A2A protocol (handles legacy /invocations URLs)
        agent_url = self._normalize_url(agent_url)

        # Build A2A request with streaming flag
        message_id = str(uuid.uuid4())
        a2a_request = self._build_a2a_request(payload, message_id)

        # Sign request with SigV4 (REQUIRED for InvokeAgentRuntime API)
        # FIX: Previous code used plain headers without SigV4 auth, causing 403 Forbidden
        headers = self._sign_request("POST", agent_url, a2a_request)

        # Override Accept header for streaming
        headers["Accept"] = "text/event-stream"

        # Add session ID if provided (after signing - not included in signature)
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


# =============================================================================
# Local Testing Support (Strands A2AServer)
# =============================================================================

class LocalA2AClient(A2AClient):
    """
    A2A Client for local development and testing.

    Connects to locally running Strands A2AServer instances without
    SSM Parameter Store or AWS authentication.

    Example:
        # Start local server: python main_a2a.py
        client = LocalA2AClient()

        # Test health check
        result = await client.invoke_agent("nexo_import", {"action": "health_check"})
        print(result.response)

        # Test Agent Card discovery
        card = await client.get_agent_card("nexo_import")
        print(f"Agent: {card.name}, Skills: {len(card.skills)}")
    """

    # Local agent URLs (port 9000, root path /)
    LOCAL_AGENTS = {
        "nexo_import": "http://127.0.0.1:9000/",
        "learning": "http://127.0.0.1:9001/",
        "validation": "http://127.0.0.1:9002/",
        "schema_evolution": "http://127.0.0.1:9003/",
        "intake": "http://127.0.0.1:9004/",
        "import": "http://127.0.0.1:9005/",
        "estoque_control": "http://127.0.0.1:9006/",
        "compliance": "http://127.0.0.1:9007/",
        "reconciliacao": "http://127.0.0.1:9008/",
        "expedition": "http://127.0.0.1:9009/",
        "carrier": "http://127.0.0.1:9010/",
        "reverse": "http://127.0.0.1:9011/",
        "observation": "http://127.0.0.1:9012/",
        "equipment_research": "http://127.0.0.1:9013/",
    }

    def __init__(self, base_port: int = 9000):
        """
        Initialize local A2A client.

        Args:
            base_port: Base port for agent servers (default 9000)
        """
        super().__init__()
        self.base_port = base_port
        self._local_mode = True

    async def get_agent_url(self, agent_id: str) -> Optional[str]:
        """
        Get local URL for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Local URL for agent
        """
        # Check environment variable override first
        env_var = f"AGENT_URL_{agent_id.upper()}"
        if env_var in os.environ:
            return os.environ[env_var]

        return self.LOCAL_AGENTS.get(agent_id)

    def _sign_request(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Skip SigV4 signing for local requests.

        Local Strands A2AServer doesn't require AWS authentication.
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


async def test_local_a2a():
    """
    Test A2A communication with locally running Strands A2AServer.

    Usage:
        cd server/agentcore-inventory
        python main_a2a.py &  # Start server in background
        python -c "import asyncio; from shared.a2a_client import test_local_a2a; asyncio.run(test_local_a2a())"
    """
    print("=" * 60)
    print("Local A2A Client Test - Strands A2AServer")
    print("=" * 60)

    client = LocalA2AClient()

    # Test 1: Agent Card Discovery
    print("\n[Test 1] Agent Card Discovery...")
    card = await client.get_agent_card("nexo_import")
    if card:
        print(f"  ✅ Agent: {card.name}")
        print(f"  ✅ Description: {card.description[:50]}...")
        print(f"  ✅ Skills: {len(card.skills)} available")
    else:
        print("  ❌ Agent Card not available")

    # Test 2: Health Check
    print("\n[Test 2] Health Check...")
    result = await client.invoke_agent("nexo_import", {"action": "health_check"})
    if result.success:
        print(f"  ✅ Status: healthy")
        print(f"  ✅ Protocol: A2A")
        print(f"  ✅ Response: {result.response[:100]}...")
    else:
        print(f"  ❌ Error: {result.error}")

    # Test 3: Agent Availability
    print("\n[Test 3] Agent Availability...")
    available = await client.validate_agent_availability("nexo_import")
    print(f"  {'✅' if available else '❌'} nexo_import: {'Available' if available else 'Not available'}")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
