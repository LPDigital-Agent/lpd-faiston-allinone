# =============================================================================
# A2A (Agent-to-Agent) Client Tool - Faiston Portal
# =============================================================================
# Client for invoking remote AgentCore agents via HTTP API.
#
# Enables NEXO Portal orchestrator to delegate queries to:
# - Faiston Academy agents (learning, flashcards, mindmaps)
# - Faiston SGA agents (inventory, stock, movements)
#
# Based on AWS Bedrock AgentCore Runtime API:
# https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/invoke-runtime.html
# =============================================================================

import os
import json
from typing import Dict, Any, Optional
from urllib.parse import quote


class A2AClient:
    """
    Client for invoking remote AgentCore agents via A2A protocol.

    This client allows the Portal NEXO agent to delegate specialized
    queries to domain-specific agents (Academy, SGA) while maintaining
    session context.
    """

    def __init__(
        self,
        target_arn: str,
        region: str = "us-east-2",
        timeout: int = 60
    ):
        """
        Initialize A2A client.

        Args:
            target_arn: ARN of the target AgentCore runtime
            region: AWS region (default: us-east-2)
            timeout: Request timeout in seconds
        """
        self.target_arn = target_arn
        self.region = region
        self.timeout = timeout
        self.endpoint = f"https://bedrock-agentcore.{region}.amazonaws.com"

    async def invoke(
        self,
        action: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke a remote AgentCore agent action.

        Args:
            action: Action name to invoke (e.g., "nexo_chat", "generate_flashcards")
            payload: Request payload for the action
            session_id: Optional session ID for context continuity
            user_id: Optional user ID for personalization

        Returns:
            Agent response dictionary
        """
        import httpx
        import boto3
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        # Build request payload
        request_payload = {
            "action": action,
            **payload
        }

        if user_id:
            request_payload["user_id"] = user_id

        # Build URL
        encoded_arn = quote(self.target_arn, safe='')
        url = f"{self.endpoint}/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if session_id:
            headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] = session_id

        # Sign request with SigV4
        body = json.dumps(request_payload)

        try:
            # Get credentials from environment (AgentCore execution role)
            session = boto3.Session()
            credentials = session.get_credentials()

            # Create AWSRequest for signing
            request = AWSRequest(
                method="POST",
                url=url,
                data=body,
                headers=headers
            )

            # Sign the request
            SigV4Auth(credentials, "bedrock-agentcore", self.region).add_auth(request)

            # Execute request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=body,
                    headers=dict(request.headers),
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"A2A invocation failed: {response.status_code}",
                        "details": response.text
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"A2A client error: {str(e)}"
            }


# =============================================================================
# Pre-configured Client Factories
# =============================================================================

def get_academy_client() -> A2AClient:
    """Get pre-configured client for Academy AgentCore."""
    from agents.utils import ACADEMY_AGENTCORE_ARN, AWS_REGION
    return A2AClient(target_arn=ACADEMY_AGENTCORE_ARN, region=AWS_REGION)


def get_sga_client() -> A2AClient:
    """Get pre-configured client for SGA Inventory AgentCore."""
    from agents.utils import SGA_AGENTCORE_ARN, AWS_REGION
    return A2AClient(target_arn=SGA_AGENTCORE_ARN, region=AWS_REGION)


# =============================================================================
# High-Level Delegation Functions
# =============================================================================

async def delegate_to_academy(
    question: str,
    user_id: str,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Delegate a learning/education query to Academy AgentCore.

    Args:
        question: User's question
        user_id: User identifier
        session_id: Optional session for context
        context: Optional additional context

    Returns:
        Academy agent response
    """
    client = get_academy_client()

    payload = {
        "question": question,
        "portal_context": {
            "source": "portal_nexo",
            "delegated_at": _get_iso_timestamp(),
            **(context or {})
        }
    }

    return await client.invoke(
        action="nexo_chat",
        payload=payload,
        session_id=session_id,
        user_id=user_id
    )


async def delegate_to_sga(
    question: str,
    user_id: str,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Delegate an inventory/stock query to SGA AgentCore.

    Args:
        question: User's question
        user_id: User identifier
        session_id: Optional session for context
        context: Optional additional context

    Returns:
        SGA agent response
    """
    client = get_sga_client()

    payload = {
        "question": question,
        "portal_context": {
            "source": "portal_nexo",
            "delegated_at": _get_iso_timestamp(),
            **(context or {})
        }
    }

    return await client.invoke(
        action="chat",  # SGA uses "chat" action
        payload=payload,
        session_id=session_id,
        user_id=user_id
    )


def _get_iso_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
