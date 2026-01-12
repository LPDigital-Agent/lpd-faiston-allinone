# =============================================================================
# A2A Client - Agent-to-Agent Communication (100% A2A Architecture)
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
# Architecture (100% A2A - NO SSM):
# - JSON-RPC 2.0 over HTTP (port 9000, path /)
# - Agent Card discovery at /.well-known/agent-card.json
# - Hardcoded runtime IDs (stable, immutable once created)
# - AgentCore Identity for authentication (SigV4)
# - X-Ray tracing for distributed observability
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
import time
import urllib.parse
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

# =============================================================================
# AgentCore Runtime IDs (100% A2A Architecture - NO SSM)
# =============================================================================
# These IDs are IMMUTABLE once created - they only change if you delete/recreate
# the runtime in Terraform. Using hardcoded IDs eliminates SSM latency (~50ms)
# and simplifies the architecture.
#
# To find runtime IDs:
#   aws bedrock-agentcore list-agent-runtimes --region us-east-2
#
# Reference: terraform/main/agentcore_runtimes.tf
# =============================================================================

RUNTIME_IDS = {
    "nexo_import": "faiston_sga_nexo_import-0zNtFDAo7M",
    "learning": "faiston_sga_learning-30cZIOFmzo",
    "validation": "faiston_sga_validation-3zgXMwCxGN",
    "observation": "faiston_sga_observation-ACVR2SDmtJ",
    "import": "faiston_sga_import-sM56rCFLIr",
    "intake": "faiston_sga_intake-9I7Nwe6ZfP",
    "estoque_control": "faiston_sga_estoque_control-jLRAIr8EcI",
    "compliance": "faiston_sga_compliance-2Kty3O64vz",
    "reconciliacao": "faiston_sga_reconciliacao-poSPdO6OKm",
    "expedition": "faiston_sga_expedition-yJ7Nb551hS",
    "carrier": "faiston_sga_carrier-fVOntdCJaZ",
    "reverse": "faiston_sga_reverse-jeiH9k8CbC",
    "schema_evolution": "faiston_sga_schema_evolution-Ke1i76BvB0",
    "equipment_research": "faiston_sga_equipment_research-xs7hxg2SfS",
}


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

    100% A2A Architecture Implementation (NO SSM):
    - Agent Card Discovery via /.well-known/agent-card.json (A2A Protocol)
    - JSON-RPC 2.0 message formatting (message/send method)
    - SigV4 authentication for AgentCore Runtime
    - Hardcoded runtime IDs (stable, immutable - NO SSM LOOKUPS)
    - X-Ray tracing integration

    Discovery Flow (A2A Protocol Compliant):
    1. Get runtime URL from hardcoded RUNTIME_IDS mapping
    2. Optionally fetch Agent Card from /.well-known/agent-card.json
    3. Cache Agent Card with TTL for subsequent calls
    4. Use URL for invocations with SigV4 signing

    Example:
        client = A2AClient()

        # Discover agent capabilities (A2A Protocol)
        card = await client.discover_agent("learning")
        if card:
            print(f"Skills: {[s['name'] for s in card.skills]}")

        # Invoke agent
        result = await client.invoke_agent("learning", {
            "action": "retrieve_prior_knowledge",
            "filename": "EXPEDIÇÃO_JAN_2026.csv"
        })

        if result.success:
            prior_knowledge = json.loads(result.response)

    Reference: https://a2a-protocol.org/latest/specification/
    """

    # Agent Card cache TTL in seconds (5 minutes)
    CARD_CACHE_TTL = 300

    def __init__(self, use_discovery: bool = True):
        """
        Initialize A2A client with Agent Card discovery support.

        Args:
            use_discovery: Enable Agent Card discovery by default (100% A2A Architecture)
        """
        self.region = os.environ.get("AWS_REGION", "us-east-2")
        self.account_id = os.environ.get("AWS_ACCOUNT_ID", "377311924364")
        self.use_discovery = use_discovery

        # Agent Card cache: {agent_id: {"card": AgentCard, "timestamp": float}}
        self._agent_cards: Dict[str, Dict] = {}

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

    def _build_runtime_url(self, agent_id: str) -> Optional[str]:
        """
        Build AgentCore runtime URL from agent ID using hardcoded runtime IDs.

        100% A2A Architecture: NO SSM LOOKUPS. Runtime IDs are stable and
        immutable - they only change if you delete/recreate the runtime.

        Args:
            agent_id: Agent identifier (e.g., "learning", "validation")

        Returns:
            AgentCore invocation URL or None if agent not found
        """
        runtime_id = RUNTIME_IDS.get(agent_id)
        if not runtime_id:
            logger.warning(f"[A2A] Unknown agent: {agent_id}")
            return None

        # Build AgentCore invocation URL
        # Format: https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations/
        arn = f"arn:aws:bedrock-agentcore:{self.region}:{self.account_id}:runtime/{runtime_id}"
        encoded_arn = urllib.parse.quote(arn, safe='')
        url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{encoded_arn}/invocations/"

        logger.debug(f"[A2A] Built URL for {agent_id}: {url[:80]}...")
        return url

    async def get_agent_url(self, agent_id: str) -> Optional[str]:
        """
        Get invocation URL for an agent.

        Uses hardcoded runtime IDs (NO SSM) for zero-latency lookups.

        Args:
            agent_id: Agent identifier (e.g., "learning", "validation")

        Returns:
            Agent invocation URL or None if not found
        """
        # Check environment variable first (for local development)
        env_var = f"AGENT_URL_{agent_id.upper()}"
        if env_var in os.environ:
            return os.environ[env_var]

        # Build URL from hardcoded runtime ID
        return self._build_runtime_url(agent_id)

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

    def _is_card_cache_valid(self, agent_id: str) -> bool:
        """
        Check if cached Agent Card is still valid (within TTL).

        Args:
            agent_id: Agent identifier

        Returns:
            True if cache entry exists and is within TTL
        """
        if agent_id not in self._agent_cards:
            return False

        cached = self._agent_cards[agent_id]
        age = time.time() - cached.get("timestamp", 0)
        return age < self.CARD_CACHE_TTL

    async def discover_agent(
        self,
        agent_id: str,
        force_refresh: bool = False,
        timeout: float = 10.0
    ) -> Optional[AgentCard]:
        """
        Discover agent via A2A Agent Card protocol with caching.

        This is the A2A-compliant way to discover agent capabilities
        before invoking them. Implements caching to avoid repeated
        network requests for frequently-used agents.

        100% A2A Architecture: This method should be the primary way
        to discover agents, replacing static SSM lookups.

        Args:
            agent_id: Agent identifier (e.g., "learning", "validation")
            force_refresh: Bypass cache and fetch fresh Agent Card
            timeout: Request timeout in seconds

        Returns:
            AgentCard with agent metadata and skills, or None if discovery fails

        Example:
            card = await client.discover_agent("learning")
            if card:
                print(f"Agent: {card.name} v{card.version}")
                print(f"Skills: {[s.get('name') for s in card.skills]}")

        Reference: https://a2a-protocol.org/latest/specification/
        """
        # Check cache first (unless force refresh)
        if not force_refresh and self._is_card_cache_valid(agent_id):
            cached = self._agent_cards[agent_id]
            logger.debug(f"[A2A] Using cached Agent Card for '{agent_id}'")
            return cached["card"]

        # Fetch fresh Agent Card
        card = await self.get_agent_card(agent_id, timeout)

        if card:
            # Cache the card
            self._agent_cards[agent_id] = {
                "card": card,
                "timestamp": time.time(),
            }
            logger.info(
                f"[A2A] Discovered agent '{agent_id}': {card.name} v{card.version} "
                f"({len(card.skills)} skills)"
            )

        return card

    def clear_card_cache(self, agent_id: Optional[str] = None) -> None:
        """
        Clear Agent Card cache.

        Args:
            agent_id: Specific agent to clear, or None to clear all
        """
        if agent_id:
            self._agent_cards.pop(agent_id, None)
            logger.debug(f"[A2A] Cleared cache for agent '{agent_id}'")
        else:
            self._agent_cards.clear()
            logger.debug("[A2A] Cleared all Agent Card cache")

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

    def _get_runtime_arn(self, agent_id: str) -> Optional[str]:
        """
        Get the full ARN for an agent runtime.

        Args:
            agent_id: Agent identifier (e.g., "learning", "validation")

        Returns:
            Full ARN string or None if agent not found
        """
        runtime_id = RUNTIME_IDS.get(agent_id)
        if not runtime_id:
            return None
        return f"arn:aws:bedrock-agentcore:{self.region}:{self.account_id}:runtime/{runtime_id}"

    async def invoke_agent(
        self,
        agent_id: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: float = 30.0,
        use_discovery: Optional[bool] = None,
    ) -> A2AResponse:
        """
        Invoke another agent via A2A protocol using boto3 SDK.

        This is the main method for cross-agent communication.

        100% A2A Architecture: Uses boto3 SDK invoke_agent_runtime() which
        correctly handles IAM role credentials from inside AgentCore Runtime.
        The A2A JSON-RPC 2.0 payload format is preserved - only the transport
        mechanism changes from HTTP direct to SDK.

        Args:
            agent_id: ID of the agent to invoke (e.g., "learning", "validation")
            payload: Payload to send (will be JSON-serialized)
            session_id: Optional session ID for context continuity
            timeout: Request timeout in seconds
            use_discovery: If True, performs Agent Card discovery first (A2A compliant).
                          If None, uses instance default (self.use_discovery).
                          If False, uses direct URL lookup (faster).

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

        Reference: https://a2a-protocol.org/latest/specification/
        """
        # Import audit emitter for event emission
        from shared.audit_emitter import AgentAuditEmitter

        # Get current agent ID from environment
        current_agent = os.environ.get("AGENT_ID", "unknown")
        audit = AgentAuditEmitter(current_agent)

        # Get runtime ARN for target agent
        runtime_arn = self._get_runtime_arn(agent_id)
        if not runtime_arn:
            return A2AResponse(
                success=False,
                response="",
                agent_id=agent_id,
                message_id="",
                error=f"Agent '{agent_id}' not found in RUNTIME_IDS",
            )

        # Emit delegation event
        audit.delegating(
            target_agent=agent_id,
            message=f"Delegando para {agent_id}...",
            session_id=session_id,
        )

        # Build A2A request (JSON-RPC 2.0 format preserved)
        message_id = str(uuid.uuid4())
        a2a_request = self._build_a2a_request(payload, message_id)

        # Generate session ID if not provided
        runtime_session_id = session_id or str(uuid.uuid4())

        try:
            boto3 = _get_boto3()

            # =================================================================
            # boto3 SDK invoke_agent_runtime() - CORRECT for AgentCore Runtime
            # =================================================================
            # This method correctly handles IAM role credentials from inside
            # the AgentCore Runtime environment. HTTP direct with manual SigV4
            # fails because the credential chain doesn't work the same way.
            # =================================================================

            # Create client with timeout configuration
            from botocore.config import Config
            config = Config(
                connect_timeout=timeout,
                read_timeout=timeout,
                retries={
                    'max_attempts': MAX_RETRIES,
                    'mode': 'adaptive'  # AWS adaptive retry with backoff + jitter
                }
            )

            client = boto3.client(
                'bedrock-agentcore',
                region_name=self.region,
                config=config
            )

            # Invoke the agent runtime
            # The payload is the A2A JSON-RPC 2.0 request - format is preserved!
            logger.info(f"[A2A] Invoking {agent_id} via boto3 SDK (ARN: {runtime_arn[:50]}...)")

            response = client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                runtimeSessionId=runtime_session_id,
                payload=json.dumps(a2a_request).encode('utf-8')
            )

            # Read response payload
            response_payload = response.get('payload')
            if response_payload:
                # response_payload is a StreamingBody, read it
                response_body = response_payload.read().decode('utf-8')
                response_data = json.loads(response_body)
                logger.debug(f"[A2A] Response from {agent_id}: {str(response_data)[:200]}...")
                return self._parse_a2a_response(response_data, agent_id, message_id)
            else:
                return A2AResponse(
                    success=False,
                    response="",
                    agent_id=agent_id,
                    message_id=message_id,
                    error="Empty response payload from agent runtime",
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[A2A] Error invoking {agent_id}: {error_msg}")
            audit.error(
                message=f"Erro ao chamar {agent_id}",
                session_id=session_id,
                error=error_msg,
            )
            return A2AResponse(
                success=False,
                response="",
                agent_id=agent_id,
                message_id=message_id,
                error=error_msg,
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
    AWS authentication. Uses hardcoded local ports instead of AgentCore URLs.

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
