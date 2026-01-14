# =============================================================================
# Agent URLs Configuration
# =============================================================================
# Runtime ID → URL mapping for A2A Protocol specialist agents.
#
# ADR-002: "Everything is an Agent" Architecture
# This file provides URL resolution for A2A client tools.
# =============================================================================

import os
import urllib.parse
from typing import Optional

# =============================================================================
# AWS Configuration
# =============================================================================
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "377311924364")

# =============================================================================
# AgentCore Runtime IDs (Source of Truth)
# =============================================================================
# These are the deployed AgentCore runtime identifiers.
# Format: {agent_name}-{random_suffix}
# =============================================================================

RUNTIME_IDS = {
    # Specialist Agents (15 total)
    "nexo_import": "faiston_sga_nexo_import-0zNtFDAo7M",
    "learning": "faiston_sga_learning-30cZIOFmzo",
    "validation": "faiston_sga_validation-3zgXMwCxGN",
    "observation": "faiston_sga_observation-ACVR2SDmtJ",
    "data_import": "faiston_sga_import-sM56rCFLIr",
    "intake": "faiston_sga_intake-9I7Nwe6ZfP",
    "estoque_control": "faiston_sga_estoque_control-jLRAIr8EcI",
    "compliance": "faiston_sga_compliance-2Kty3O64vz",
    "reconciliacao": "faiston_sga_reconciliacao-poSPdO6OKm",
    "expedition": "faiston_sga_expedition-yJ7Nb551hS",
    "carrier": "faiston_sga_carrier-fVOntdCJaZ",
    "reverse": "faiston_sga_reverse-jeiH9k8CbC",
    "schema_evolution": "faiston_sga_schema_evolution-Ke1i76BvB0",
    "equipment_research": "faiston_sga_equipment_research-xs7hxg2SfS",
    # Note: enrichment not yet deployed to AgentCore
}

# =============================================================================
# Orchestrator Runtime IDs
# =============================================================================
# Orchestrators can also be invoked via A2A by other orchestrators.
# =============================================================================

ORCHESTRATOR_RUNTIME_IDS = {
    "estoque": "faiston_asset_management-uSuLPsFQNH",
    # Future orchestrators:
    # "expedicao": "faiston_sga_expedicao-XXXXX",
    # "reversa": "faiston_sga_reversa-XXXXX",
    # "rastreabilidade": "faiston_sga_rastreabilidade-XXXXX",
}

# =============================================================================
# URL Generation Functions
# =============================================================================


def get_agent_arn(
    runtime_id: str,
    region: str = AWS_REGION,
    account_id: str = AWS_ACCOUNT_ID,
) -> str:
    """
    Build AgentCore runtime ARN.

    Args:
        runtime_id: AgentCore runtime identifier
        region: AWS region
        account_id: AWS account ID

    Returns:
        Full ARN string
    """
    return f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/{runtime_id}"


def get_agent_url(
    agent_id: str,
    region: str = AWS_REGION,
    account_id: str = AWS_ACCOUNT_ID,
) -> Optional[str]:
    """
    Get invocation URL for an agent.

    Checks environment variables first (for local development),
    then falls back to RUNTIME_IDS mapping.

    Args:
        agent_id: Agent identifier (e.g., "learning", "validation")
        region: AWS region
        account_id: AWS account ID

    Returns:
        Agent invocation URL or None if not found
    """
    # Check environment variable first (for local development)
    env_var = f"AGENT_URL_{agent_id.upper()}"
    if env_var in os.environ:
        return os.environ[env_var]

    # Look up in RUNTIME_IDS (specialists first, then orchestrators)
    runtime_id = RUNTIME_IDS.get(agent_id) or ORCHESTRATOR_RUNTIME_IDS.get(agent_id)
    if not runtime_id:
        return None

    # Build AgentCore invocation URL
    # Format: https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations/
    arn = get_agent_arn(runtime_id, region, account_id)
    encoded_arn = urllib.parse.quote(arn, safe="")
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations/"


def get_all_specialist_urls(
    region: str = AWS_REGION,
    account_id: str = AWS_ACCOUNT_ID,
) -> dict:
    """
    Get URLs for all specialist agents.

    Returns:
        Dict mapping agent_id to URL
    """
    return {
        agent_id: get_agent_url(agent_id, region, account_id)
        for agent_id in RUNTIME_IDS
    }


# =============================================================================
# Pre-computed SPECIALIST_URLS for Import
# =============================================================================
# This is the main export for orchestrators to use.
# URLs are lazily computed on first access.
# =============================================================================


class _LazySpecialistUrls(dict):
    """Lazy dictionary that computes URLs on first access."""

    _initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            for agent_id in RUNTIME_IDS:
                url = get_agent_url(agent_id)
                if url:
                    self[agent_id] = url
            self._initialized = True

    def __getitem__(self, key):
        self._ensure_initialized()
        return super().__getitem__(key)

    def __iter__(self):
        self._ensure_initialized()
        return super().__iter__()

    def items(self):
        self._ensure_initialized()
        return super().items()

    def keys(self):
        self._ensure_initialized()
        return super().keys()

    def values(self):
        self._ensure_initialized()
        return super().values()


SPECIALIST_URLS = _LazySpecialistUrls()
