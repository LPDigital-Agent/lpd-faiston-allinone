# =============================================================================
# Swarm Response Extraction Utilities (BUG-019)
# =============================================================================
# Infrastructure code for extracting structured data from Strands Swarm results.
#
# These utilities follow the OFFICIAL Strands pattern for accessing agent results:
# - Primary: result.results["agent_name"].result
# - Fallback: result.entry_point.messages (for tool_result blocks)
#
# ToolResult format (official Strands SDK):
# {
#     "toolUseId": str,       # Optional
#     "status": str,          # "success" or "error"
#     "content": [            # List of content items
#         {"json": {...}},    # Structured data
#         {"text": "..."}     # Text data
#     ]
# }
#
# VALIDATION (2026-01-15):
# - Follows official Strands Swarm documentation patterns
# - No SDK utility exists - this fills the gap
# - Is INFRASTRUCTURE code (SDK parsing), NOT business logic
# - Business logic runs 100% inside Strands agents with Gemini
#
# Sources:
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/
# - https://strandsagents.com/latest/documentation/docs/api-reference/multiagent/
# - https://github.com/strands-agents/docs/blob/main/docs/user-guide/concepts/tools/custom-tools.md
# =============================================================================

import json
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# BUG-020 v4 FIX: Helper function to unwrap ToolResult format
# =============================================================================


def _unwrap_tool_result(data: Any) -> Optional[Dict]:
    """
    Unwrap ToolResult format and validate response structure.

    Handles two formats:
    - ToolResult format: {"status": "...", "content": [{"json": {...}}]}
    - Direct response: {"success": ..., "analysis": {...}}

    The ToolResult format is the official Strands SDK tool return format.
    Reference: https://strandsagents.com SDK examples

    Args:
        data: Raw data to unwrap (dict, str, or other)

    Returns:
        Unwrapped dict with "analysis" or "success" key, or None if invalid

    Example:
        >>> tool_output = {"status": "success", "content": [{"json": {"analysis": {...}}}]}
        >>> unwrapped = _unwrap_tool_result(tool_output)
        >>> print(unwrapped)  # {"analysis": {...}}
    """
    # BUG-020 v6: Diagnostic logging for extraction debugging
    logger.info(
        "[_unwrap] input type=%s, has_content=%s, has_analysis=%s, has_success=%s",
        type(data).__name__ if data else "None",
        "content" in data if isinstance(data, dict) else False,
        "analysis" in data if isinstance(data, dict) else False,
        "success" in data if isinstance(data, dict) else False,
    )

    if not isinstance(data, dict):
        return None

    # Priority 1: Handle ToolResult format
    # {"status": "success", "content": [{"json": {...actual data...}}]}
    if "content" in data and isinstance(data["content"], list):
        for content_item in data["content"]:
            if isinstance(content_item, dict) and "json" in content_item:
                inner = content_item["json"]
                if isinstance(inner, dict) and ("analysis" in inner or "success" in inner):
                    logger.debug("[_unwrap] Extracted from ToolResult format")
                    return inner

    # Priority 2: Direct valid response (backwards compatibility)
    if "analysis" in data or "success" in data:
        return data

    return None


def _extract_tool_output_from_swarm_result(
    swarm_result: Any,
    agent_name: str = "",
    tool_name: str = "",
) -> Optional[Dict]:
    """
    Extract tool output from a Strands Swarm result.

    Uses the OFFICIAL Strands pattern: result.results["agent_name"].result

    Handles multiple formats (priority order):
    1. result.results[agent_name].result (official Strands pattern)
    2. result.results[agent_name].result as JSON string
    3. ToolResult format: {"status": "...", "content": [{"json": {...}}]}
    4. result.entry_point.messages[] (fallback for tool_result blocks)
    5. Iterate all results if agent_name not specified

    Args:
        swarm_result: Result from swarm() invocation (MultiAgentResult/SwarmResult)
        agent_name: Name of the agent to extract results from (e.g., "file_analyst")
        tool_name: Name of the tool for logging (e.g., "unified_analyze_file")

    Returns:
        Extracted dict or None if no valid output found

    Example:
        >>> result = swarm("Analyze file.csv")
        >>> data = _extract_tool_output_from_swarm_result(
        ...     result, agent_name="file_analyst", tool_name="unified_analyze_file"
        ... )
        >>> if data:
        ...     print(data["analysis"])
    """
    if swarm_result is None:
        logger.warning("[_extract] swarm_result is None!")
        return None

    # BUG-020 v6: Diagnostic logging for Swarm result structure
    logger.info(
        "[_extract] START: swarm_result type=%s, has_results=%s, has_entry_point=%s",
        type(swarm_result).__name__,
        hasattr(swarm_result, "results") and bool(swarm_result.results),
        hasattr(swarm_result, "entry_point") and bool(swarm_result.entry_point),
    )
    if hasattr(swarm_result, "results") and swarm_result.results:
        logger.info("[_extract] results_keys=%s", list(swarm_result.results.keys()))

    # -------------------------------------------------------------------------
    # Priority 1: Extract from specific agent's result (official Strands pattern)
    # Reference: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/
    # Pattern: result.results["analyst"].result
    # -------------------------------------------------------------------------
    if hasattr(swarm_result, "results") and swarm_result.results:
        # Priority 1: Try specific agent name if provided AND exists (official pattern)
        if agent_name and agent_name in swarm_result.results:
            agent_result = swarm_result.results[agent_name]
            extracted = _extract_from_agent_result(agent_result, agent_name, tool_name)
            if extracted:
                return extracted

        # Priority 2: Iterate ALL agents as fallback
        # BUG-020 v3 FIX: This now runs unconditionally when Priority 1 fails
        # (when agent_name not found in results OR agent_name not provided)
        for name, agent_result in swarm_result.results.items():
            extracted = _extract_from_agent_result(agent_result, name, tool_name)
            if extracted:
                logger.debug(
                    "[_extract] Found valid output from agent %s (fallback iteration)",
                    name,
                )
                return extracted

    # -------------------------------------------------------------------------
    # Priority 2: Extract from entry_point messages (fallback)
    # Used when Swarm returns natural language with embedded tool_result
    # -------------------------------------------------------------------------
    if hasattr(swarm_result, "entry_point") and swarm_result.entry_point:
        if hasattr(swarm_result.entry_point, "messages"):
            extracted = _extract_from_messages(swarm_result.entry_point.messages, tool_name)
            if extracted:
                return extracted

    # -------------------------------------------------------------------------
    # Priority 3: Direct message attribute
    # Some Swarm results have a direct .message property with JSON
    # -------------------------------------------------------------------------
    if hasattr(swarm_result, "message") and swarm_result.message and isinstance(swarm_result.message, str):
        try:
            data = json.loads(swarm_result.message)
            if isinstance(data, dict):
                logger.debug("[_extract] Found JSON in direct message attribute")
                return data
        except json.JSONDecodeError:
            pass

    logger.debug(
        "[_extract] No valid structured output found in swarm result for agent=%s tool=%s",
        agent_name,
        tool_name,
    )
    return None


def _extract_from_agent_result(
    agent_result: Any,
    agent_name: str,
    tool_name: str,
) -> Optional[Dict]:
    """
    Extract structured data from a single agent's result.

    Handles:
    - Direct dict result
    - JSON string result
    - ToolResult format: {"status": "...", "content": [{"json": {...}}]}

    Uses _unwrap_tool_result() helper for consistent handling (BUG-020 v4).
    """
    # BUG-020 v6: Diagnostic logging for agent result details
    logger.info(
        "[_extract_agent] agent=%s, has_result_attr=%s, result_type=%s",
        agent_name,
        hasattr(agent_result, "result"),
        type(agent_result.result).__name__ if hasattr(agent_result, "result") and agent_result.result else "None",
    )

    if not hasattr(agent_result, "result") or not agent_result.result:
        logger.warning("[_extract_agent] agent=%s has NO result attribute!", agent_name)
        return None

    result_data = agent_result.result

    # =========================================================================
    # BUG-020 v7 FIX: Handle nested AgentResult objects
    # =========================================================================
    # CloudWatch logs revealed: result_type=AgentResult instead of dict
    # Strands SDK may return AgentResult.result as another AgentResult object.
    # This while loop unwraps until we get actual data (dict or str).
    # =========================================================================
    unwrap_depth = 0
    max_unwrap_depth = 5  # Safety limit to prevent infinite loops
    while (
        hasattr(result_data, "result")
        and not isinstance(result_data, (dict, str))
        and unwrap_depth < max_unwrap_depth
    ):
        logger.debug(
            "[_extract_agent] Unwrapping nested AgentResult for agent=%s (depth=%d)",
            agent_name,
            unwrap_depth,
        )
        result_data = result_data.result
        unwrap_depth += 1

    if unwrap_depth > 0:
        logger.info(
            "[_extract_agent] agent=%s unwrapped %d levels, final_type=%s",
            agent_name,
            unwrap_depth,
            type(result_data).__name__,
        )

    # Handle string JSON (LLM may return JSON as string)
    if isinstance(result_data, str):
        try:
            result_data = json.loads(result_data)
        except json.JSONDecodeError:
            logger.debug(
                "[_extract] Agent %s result is non-JSON string, skipping",
                agent_name,
            )
            return None

    if not isinstance(result_data, dict):
        # BUG-020 v7: Enhanced logging for debugging unexpected types
        logger.warning(
            "[_extract_agent] agent=%s result_data is NOT a dict! type=%s, attrs=%s",
            agent_name,
            type(result_data).__name__,
            [a for a in dir(result_data) if not a.startswith("_")][:10] if hasattr(result_data, "__dir__") else "N/A",
        )
        return None

    # BUG-020 v4: Use helper for consistent ToolResult and direct format handling
    unwrapped = _unwrap_tool_result(result_data)
    if unwrapped:
        logger.debug(
            "[_extract] Found valid result from agent %s",
            agent_name,
        )
        return unwrapped

    # Additional fallback: Text content in ToolResult format
    # (edge case not handled by _unwrap_tool_result)
    if "content" in result_data and isinstance(result_data["content"], list):
        for content_item in result_data["content"]:
            if isinstance(content_item, dict) and "text" in content_item:
                try:
                    text_data = json.loads(content_item["text"])
                    if isinstance(text_data, dict) and ("analysis" in text_data or "success" in text_data):
                        logger.debug(
                            "[_extract] Parsed JSON from text content, agent %s",
                            agent_name,
                        )
                        return text_data
                except json.JSONDecodeError:
                    pass

    return None


def _extract_from_messages(messages: list, tool_name: str) -> Optional[Dict]:
    """
    Extract structured data from entry_point messages.

    Searches for tool_result blocks in message history.
    Handles both direct JSON and ToolResult format (BUG-020 v4 fix).
    """
    for msg in reversed(messages if isinstance(messages, list) else []):
        # Handle dict-style messages
        if isinstance(msg, dict):
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        block_content = block.get("content", "")
                        try:
                            data = json.loads(block_content) if isinstance(block_content, str) else block_content
                            # BUG-020 v4 FIX: Use helper to handle ToolResult format
                            unwrapped = _unwrap_tool_result(data)
                            if unwrapped:
                                logger.debug("[_extract] Found JSON in tool_result block")
                                return unwrapped
                        except (json.JSONDecodeError, TypeError):
                            continue

        # Handle object-style messages
        if hasattr(msg, "content") and msg.content:
            try:
                data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                # BUG-020 v4 FIX: Use helper to handle ToolResult format
                unwrapped = _unwrap_tool_result(data)
                if unwrapped:
                    logger.debug("[_extract] Found JSON in entry_point messages")
                    return unwrapped
            except (json.JSONDecodeError, TypeError):
                continue

    return None


def _process_swarm_result(
    swarm_result: Any,
    session: Dict,
    action: str = "",
) -> Dict:
    """
    Process Swarm result and update session context.

    This function:
    1. Extracts structured data from the Swarm result
    2. Updates session context with analysis data, mappings, questions
    3. Returns a standardized response dict

    Priority order for extraction:
    1. Use results dict first (most reliable - official Strands pattern)
    2. Fall back to message JSON
    3. Extract JSON from natural language text
    4. Store raw message as fallback

    Args:
        swarm_result: Result from swarm() invocation
        session: Session dict to update with context (modified in-place)
        action: Action name for logging/tracking

    Returns:
        Processed response dict with at minimum:
        - success: bool
        - action: str
        - session_id: str
        Plus any extracted data (analysis, column_mappings, questions, etc.)

    Example:
        >>> session = {"context": {}, "awaiting_response": False}
        >>> result = swarm("Analyze inventory.csv")
        >>> response = _process_swarm_result(result, session, action="analyze_file")
        >>> print(response["success"])
        True
    """
    response = {
        "success": False,
        "action": action,
        "session_id": session.get("session_id", ""),
    }

    # Ensure session has context dict
    if "context" not in session:
        session["context"] = {}

    # -------------------------------------------------------------------------
    # Try structured extraction first (most reliable - official Strands pattern)
    # -------------------------------------------------------------------------
    extracted = _extract_tool_output_from_swarm_result(swarm_result)
    if extracted:
        response.update(extracted)
        response["success"] = extracted.get("success", True)

        # Update session context with extracted data
        # Use the SAME keys as extracted (analysis, proposed_mappings, etc.)
        if "analysis" in extracted:
            session["context"]["analysis"] = extracted["analysis"]
            logger.debug("[_process] Updated session with analysis")

        if "proposed_mappings" in extracted:
            session["context"]["proposed_mappings"] = extracted["proposed_mappings"]
            logger.debug("[_process] Updated session with proposed_mappings")

        if "column_mappings" in extracted:
            session["context"]["proposed_mappings"] = extracted["column_mappings"]
            logger.debug("[_process] Updated session with column_mappings -> proposed_mappings")

        if "unmapped_columns" in extracted:
            session["context"]["unmapped_columns"] = extracted["unmapped_columns"]
            logger.debug("[_process] Updated session with unmapped_columns")

        if "questions" in extracted:
            session["context"]["hil_questions"] = extracted["questions"]
            if extracted["questions"]:
                session["awaiting_response"] = True
                logger.debug("[_process] Set awaiting_response=True (HIL questions)")

        return response

    # -------------------------------------------------------------------------
    # Fallback: Try to extract JSON from message text
    # -------------------------------------------------------------------------
    if hasattr(swarm_result, "message") and swarm_result.message and isinstance(swarm_result.message, str):
        message = swarm_result.message

        # Try direct JSON parse
        try:
            data = json.loads(message)
            response.update(data)
            response["success"] = True
            logger.debug("[_process] Extracted JSON from message directly")
            return response
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in text (LLM sometimes wraps JSON in explanation)
        json_match = re.search(r'\{[\s\S]*\}', message)
        if json_match:
            try:
                data = json.loads(json_match.group())
                response.update(data)
                response["success"] = True
                logger.debug("[_process] Extracted JSON block from message text")
                return response
            except json.JSONDecodeError:
                pass

        # Store raw message as fallback (at least preserve the response)
        response["message"] = message
        response["success"] = True
        logger.debug("[_process] Stored raw message as fallback")

    return response
