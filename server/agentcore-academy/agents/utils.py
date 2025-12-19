# =============================================================================
# Shared Utilities for Faiston Academy Agents
# =============================================================================
# Common helpers used across all Gemini-native agents.
#
# Note: Adapted from Hive Academy for Faiston One platform.
# All agents use Gemini 3.0 Pro exclusively.
#
# API Key Note:
# GOOGLE_API_KEY is passed via --env at deploy time (not runtime SSM lookup).
# This follows the AWS official example pattern.
# =============================================================================

import json
import re
from typing import Dict, Any

# =============================================================================
# Constants
# =============================================================================

# App name for Google ADK sessions
APP_NAME = "faiston-academy"

# Agent version for tracking
AGENT_VERSION = "2025.12.19.v1"

# Model ID - All agents use Gemini 3.0 Pro
MODEL_GEMINI = "gemini-3-pro-preview"


# =============================================================================
# JSON Parsing Utilities
# =============================================================================


def extract_json(response: str) -> str:
    """
    Extract JSON from a response that may contain markdown code blocks.

    Args:
        response: Raw response text from LLM

    Returns:
        Extracted JSON string
    """
    # Try to find JSON in markdown code block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if json_match:
        return json_match.group(1).strip()

    # Try to find raw JSON object or array
    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response)
    if json_match:
        return json_match.group(1).strip()

    # Return as-is if no JSON found
    return response.strip()


def parse_json_safe(response: str) -> Dict[str, Any]:
    """
    Safely parse JSON from response with fallback.

    Args:
        response: Raw response text from LLM

    Returns:
        Parsed JSON dict or error dict
    """
    try:
        json_str = extract_json(response)
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON: {e}", "raw_response": response}
