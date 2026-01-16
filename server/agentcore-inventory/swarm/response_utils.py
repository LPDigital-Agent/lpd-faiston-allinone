# =============================================================================
# Swarm Response Extraction Utilities (BUG-019 + BUG-020 v12)
# =============================================================================
# Infrastructure code for extracting structured data from Strands Swarm results.
#
# Official Strands AgentResult structure (SDK v1.20.0):
# @dataclass
# class AgentResult:
#     stop_reason: StopReason
#     message: Message          # ← Tool output is HERE (can be dict or Message)
#     metrics: EventLoopMetrics
#     state: Any
#     interrupts: Sequence[Interrupt] | None = None
#     structured_output: BaseModel | None = None
#
# Extraction paths (priority order):
# 1. result.results["agent_name"].result.message (BUG-020 v8 - CORRECT)
# 2. result.results["agent_name"].result as dict (fallback for raw dict returns)
# 3. result.entry_point.messages[] (fallback for tool_result blocks)
#
# Message content block format (OFFICIAL Strands SDK - v11 FIX):
# Content blocks use DIRECT KEYS, NOT a "type" field!
# {
#     "role": "user",
#     "content": [
#         {"text": "..."},           # Text block
#         {"toolUse": {...}},        # Tool use block
#         {"toolResult": {...}}      # Tool result block ← OUR DATA IS HERE
#     ]
# }
#
# ToolResult format (official Strands SDK):
# {
#     "toolUseId": str,       # Optional
#     "status": str,          # "success" or "error"
#     "content": [            # List of content items
#         {"json": {...}},    # Structured data ← ANALYSIS HERE
#         {"text": "..."}     # Text data (may be JSON string)
#     ]
# }
#
# VALIDATION (2026-01-15):
# - Follows official Strands Swarm documentation patterns
# - No SDK utility exists - this fills the gap
# - Is INFRASTRUCTURE code (SDK parsing), NOT business logic
# - Business logic runs 100% inside Strands agents with Gemini
#
# BUG-020 v11 FIX (2026-01-16):
# - v10 looked for content_block.get("type") == "tool_result" - WRONG!
# - Official Strands SDK uses "toolResult" as a KEY, NOT a type value
# - v11 checks for "toolResult" in content_block (correct pattern)
# - Extracts from content_block["toolResult"]["content"][0]["json"]
#
# BUG-020 v12 FIX (2026-01-16):
# - CloudWatch revealed the REAL format produced by Strands SDK tools:
#   {"<tool_name>_response": {"output": [{"text": "{'success': True, ...}"}]}}
# - Key is <tool_name>_response (e.g., unified_analyze_file_response), NOT toolResult!
# - Content is Python repr STRING with SINGLE QUOTES, NOT valid JSON!
# - v12 checks for key.endswith("_response") pattern
# - Uses ast.literal_eval() as fallback for Python repr strings
# - CloudWatch evidence: 2026-01-16 12:49:38 shows exact format
#
# Sources:
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/
# - https://strandsagents.com/latest/documentation/docs/api-reference/agent (tool result format)
# - https://github.com/strands-agents/docs/blob/main/docs/user-guide/concepts/tools/custom-tools.md
# - https://github.com/strands-agents/sdk-python/blob/v1.20.0/src/strands/agent/agent_result.py
# - Context7 query 2026-01-16 (confirmed toolResult key format)
# =============================================================================

import ast  # v12: For parsing Python repr strings (single quotes)
import json
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# BUG-020 v13 FIX: Helper function for _response wrapper extraction
# =============================================================================
# CloudWatch revealed: The "_response" wrapper is INSIDE parsed JSON strings,
# NOT at the content_block level where v12 was looking.
#
# Data flow:
# 1. content_block = {"type": "tool_result", "content": "JSON_STRING"}
# 2. json.loads(content_block["content"]) → {"unified_analyze_file_response": {...}}
# 3. v13 checks HERE (after json.loads) for _response pattern
#
# v12 checked content_block.keys() → ["type", "content"] → No _response found!
# v13 checks parsed.keys() → ["unified_analyze_file_response"] → Found!
# =============================================================================


def _extract_from_response_wrapper(data: Any) -> Optional[Dict]:
    """
    Extract data from Strands SDK tool response wrapper format.

    BUG-020 v13 FIX: This helper extracts from the wrapper format produced by
    Strands SDK @tool decorated functions:
    {"<tool_name>_response": {"output": [{"text": "{'success': True, ...}"}]}}

    The text content may be:
    - JSON with double quotes (valid JSON)
    - Python repr with single quotes (requires ast.literal_eval)

    This helper is called AFTER json.loads() at every extraction point where
    the wrapper might appear.

    Args:
        data: Parsed dict that may contain a _response wrapper

    Returns:
        Extracted dict with "analysis" or "success" key, or None if no wrapper found
    """
    if not isinstance(data, dict):
        return None

    for key in data.keys():
        if key.endswith("_response"):
            logger.info("[v13] Found _response wrapper: %s", key)
            wrapper = data[key]

            if isinstance(wrapper, dict) and "output" in wrapper:
                for output_item in wrapper.get("output", []):
                    if isinstance(output_item, dict):
                        # Check "text" key (most common - Strands SDK format)
                        if "text" in output_item:
                            text_content = output_item["text"]
                            logger.debug(
                                "[v13] Processing text content, type=%s, len=%d",
                                type(text_content).__name__,
                                len(text_content) if isinstance(text_content, str) else 0,
                            )

                            if isinstance(text_content, str):
                                # Try JSON first (double quotes)
                                try:
                                    parsed = json.loads(text_content)
                                    if isinstance(parsed, dict) and (
                                        "analysis" in parsed or "success" in parsed
                                    ):
                                        logger.info(
                                            "[v13] SUCCESS: Extracted from _response.output[].text (JSON)"
                                        )
                                        return parsed
                                except json.JSONDecodeError:
                                    # Try Python repr (single quotes)
                                    try:
                                        parsed = ast.literal_eval(text_content)
                                        if isinstance(parsed, dict) and (
                                            "analysis" in parsed or "success" in parsed
                                        ):
                                            logger.info(
                                                "[v13] SUCCESS: Extracted from _response.output[].text (repr)"
                                            )
                                            return parsed
                                    except (ValueError, SyntaxError) as e:
                                        logger.debug("[v13] ast.literal_eval failed: %s", e)

                            elif isinstance(text_content, dict):
                                if "analysis" in text_content or "success" in text_content:
                                    logger.info(
                                        "[v13] SUCCESS: Direct dict from _response.output[].text"
                                    )
                                    return text_content

                        # Check "json" key (alternative format)
                        if "json" in output_item:
                            inner = output_item["json"]
                            if isinstance(inner, dict) and (
                                "analysis" in inner or "success" in inner
                            ):
                                logger.info(
                                    "[v13] SUCCESS: Extracted from _response.output[].json"
                                )
                                return inner

    return None


# =============================================================================
# BUG-020 v8 FIX: Extract from AgentResult.message
# =============================================================================
# CloudWatch logs revealed: AgentResult has .message, NOT nested .result!
# The .message attribute contains tool output as JSON string or Message object.
# =============================================================================


def _extract_from_agent_message(message: Any) -> Optional[Dict]:
    """
    Extract structured data from AgentResult.message attribute.

    BUG-020 v8 FIX: This is the CORRECT extraction path!
    AgentResult.message contains the tool output, NOT AgentResult.result.

    Handles multiple message formats:
    1. JSON string with tool response wrapper: {"<tool>_response": {"output": [{"json": {...}}]}}
    2. Message object with .content array containing tool_result blocks
    3. Direct JSON string without wrapper

    Args:
        message: The AgentResult.message value (str or Message object)

    Returns:
        Extracted dict with "analysis" or "success" key, or None if invalid
    """
    if message is None:
        return None

    logger.debug(
        "[v8] _extract_from_agent_message: type=%s",
        type(message).__name__,
    )

    # Handle Message object with content array (Strands Message type)
    if hasattr(message, "content") and message.content:
        content = message.content

        # Content can be a list of content blocks
        if isinstance(content, list):
            for content_block in content:
                if isinstance(content_block, dict):
                    # Check for tool_result type
                    if content_block.get("type") == "tool_result":
                        tool_content = content_block.get("content", "")
                        if isinstance(tool_content, str):
                            try:
                                parsed = json.loads(tool_content)
                                unwrapped = _unwrap_tool_result(parsed)
                                if unwrapped:
                                    logger.info("[v8] Extracted from Message.content tool_result")
                                    return unwrapped
                            except json.JSONDecodeError:
                                pass
                        elif isinstance(tool_content, dict):
                            unwrapped = _unwrap_tool_result(tool_content)
                            if unwrapped:
                                logger.info("[v8] Extracted from Message.content dict")
                                return unwrapped

                    # Check for direct json key
                    if "json" in content_block:
                        inner = content_block["json"]
                        if isinstance(inner, dict):
                            unwrapped = _unwrap_tool_result(inner)
                            if unwrapped:
                                logger.info("[v8] Extracted from Message.content json key")
                                return unwrapped

        # Content can be a string
        elif isinstance(content, str):
            try:
                parsed = json.loads(content)
                unwrapped = _unwrap_tool_result(parsed)
                if unwrapped:
                    logger.info("[v8] Extracted from Message.content string")
                    return unwrapped
            except json.JSONDecodeError:
                pass

    # Handle JSON string message (most common case from CloudWatch logs)
    if isinstance(message, str):
        try:
            parsed = json.loads(message)
            if isinstance(parsed, dict):
                # Check for tool response wrapper format
                # Format: {"<tool_name>_response": {"output": [{"json": {...}}]}} OR
                #         {"<tool_name>_response": {"output": [{"text": "{'success': True, ...}"}]}}
                for key, value in parsed.items():
                    if key.endswith("_response") and isinstance(value, dict):
                        logger.info("[v12] Found tool_response wrapper in JSON string: %s", key)
                        output = value.get("output", [])
                        if isinstance(output, list):
                            for item in output:
                                if isinstance(item, dict):
                                    # v12 FIX: Check for "text" key with Python repr
                                    if "text" in item:
                                        text_val = item["text"]
                                        if isinstance(text_val, str):
                                            # Try JSON first, then Python repr
                                            try:
                                                inner = json.loads(text_val)
                                            except json.JSONDecodeError:
                                                try:
                                                    inner = ast.literal_eval(text_val)
                                                except (ValueError, SyntaxError):
                                                    continue
                                            if isinstance(inner, dict) and (
                                                "analysis" in inner or "success" in inner
                                            ):
                                                logger.info(
                                                    "[v12] SUCCESS: Extracted from tool_response.output[].text"
                                                )
                                                return inner
                                        elif isinstance(text_val, dict):
                                            if "analysis" in text_val or "success" in text_val:
                                                logger.info(
                                                    "[v12] SUCCESS: Direct dict from tool_response.output[].text"
                                                )
                                                return text_val

                                    # Check for "json" key (original format)
                                    if "json" in item:
                                        inner = item["json"]
                                        if isinstance(inner, dict):
                                            # Use unwrap helper or return directly
                                            unwrapped = _unwrap_tool_result(inner)
                                            if unwrapped:
                                                logger.info("[v8] Extracted from tool_response wrapper")
                                                return unwrapped
                                            # Direct return if has analysis/success
                                            if "analysis" in inner or "success" in inner:
                                                logger.info("[v8] Direct return from tool_response inner")
                                                return inner

                # Try direct unwrap (ToolResult format or direct response)
                unwrapped = _unwrap_tool_result(parsed)
                if unwrapped:
                    logger.info("[v8] Extracted from direct JSON string")
                    return unwrapped

                # Fallback: direct dict with analysis/success
                if "analysis" in parsed or "success" in parsed:
                    logger.info("[v8] Direct dict from JSON string")
                    return parsed

        except json.JSONDecodeError:
            logger.debug("[v8] Message is non-JSON string, skipping")
            pass

    # Handle dict message directly (v11 FIX for Message-like dicts)
    if isinstance(message, dict):
        # v11 FIX: Check if dict has Message structure (role + content array)
        # NOTE: hasattr(dict, "content") returns FALSE for dicts - use "key in dict"
        if "content" in message and isinstance(message.get("content"), list):
            logger.info("[v11] Dict has Message structure, iterating content array")
            for content_block in message["content"]:
                if isinstance(content_block, dict):
                    # v13 DEBUG: Log content_block structure to trace data flow
                    logger.info(
                        "[v13-DEBUG] content_block type=%s, keys=%s",
                        type(content_block).__name__,
                        list(content_block.keys())[:5],
                    )
                    # =====================================================
                    # v11 FIX: Check for "toolResult" KEY (official Strands)
                    # NOT "type": "tool_result" - that format doesn't exist!
                    # Official format: {"toolResult": {"status": "...", "content": [...]}}
                    # Source: Context7 query of strandsagents.com 2026-01-16
                    # =====================================================
                    if "toolResult" in content_block:
                        tool_result = content_block["toolResult"]
                        logger.info(
                            "[v11] Found toolResult block, status=%s",
                            tool_result.get("status") if isinstance(tool_result, dict) else "N/A",
                        )

                        # Extract from ToolResult.content array
                        # Format: {"status": "success", "content": [{"json": {...}}, {"text": "..."}]}
                        if isinstance(tool_result, dict) and "content" in tool_result:
                            for tr_content in tool_result.get("content", []):
                                if isinstance(tr_content, dict):
                                    # json block (structured data) - PRIMARY
                                    if "json" in tr_content:
                                        inner = tr_content["json"]
                                        if isinstance(inner, dict):
                                            if "analysis" in inner or "success" in inner:
                                                logger.info("[v11] SUCCESS: Extracted from toolResult.content[].json")
                                                return inner
                                            # Try unwrap if nested in another wrapper
                                            unwrapped = _unwrap_tool_result(inner)
                                            if unwrapped:
                                                logger.info("[v11] SUCCESS: Unwrapped from toolResult.content[].json")
                                                return unwrapped

                                    # text block (JSON string) - SECONDARY
                                    if "text" in tr_content:
                                        try:
                                            parsed = json.loads(tr_content["text"])
                                            if isinstance(parsed, dict):
                                                if "analysis" in parsed or "success" in parsed:
                                                    logger.info("[v11] SUCCESS: Parsed from toolResult.content[].text")
                                                    return parsed
                                                unwrapped = _unwrap_tool_result(parsed)
                                                if unwrapped:
                                                    logger.info("[v11] SUCCESS: Unwrapped from toolResult.content[].text")
                                                    return unwrapped
                                        except json.JSONDecodeError:
                                            logger.debug("[v11] text content is not JSON")

                        # Fallback: Direct data in toolResult (non-standard but handle it)
                        if isinstance(tool_result, dict):
                            if "analysis" in tool_result or "success" in tool_result:
                                logger.info("[v11] SUCCESS: Direct data from toolResult")
                                return tool_result

                    # =====================================================
                    # v12 FIX: Check for "<tool_name>_response" KEY
                    # Strands SDK wraps @tool returns in this format!
                    # Format: {"<tool>_response": {"output": [{"text": "..."}]}}
                    # Source: CloudWatch logs 2026-01-16 12:49:38
                    # =====================================================
                    for key in content_block.keys():
                        if key.endswith("_response"):
                            logger.info("[v12] Found tool_response wrapper: %s", key)
                            wrapper = content_block[key]

                            if isinstance(wrapper, dict) and "output" in wrapper:
                                for output_item in wrapper.get("output", []):
                                    if isinstance(output_item, dict):
                                        # Check for "text" key (Strands SDK format)
                                        if "text" in output_item:
                                            text_content = output_item["text"]
                                            logger.info(
                                                "[v12] Found text in output, length=%d",
                                                len(text_content) if text_content else 0,
                                            )

                                            # Try JSON first (double quotes)
                                            if isinstance(text_content, str):
                                                try:
                                                    parsed = json.loads(text_content)
                                                    if isinstance(parsed, dict):
                                                        if "analysis" in parsed or "success" in parsed:
                                                            logger.info(
                                                                "[v12] SUCCESS: Parsed JSON from tool_response.output[].text"
                                                            )
                                                            return parsed
                                                except json.JSONDecodeError:
                                                    # Python repr with single quotes - use ast.literal_eval
                                                    try:
                                                        parsed = ast.literal_eval(text_content)
                                                        if isinstance(parsed, dict):
                                                            if "analysis" in parsed or "success" in parsed:
                                                                logger.info(
                                                                    "[v12] SUCCESS: Parsed Python repr from tool_response.output[].text"
                                                                )
                                                                return parsed
                                                    except (ValueError, SyntaxError) as e:
                                                        logger.debug("[v12] ast.literal_eval failed: %s", e)

                                            elif isinstance(text_content, dict):
                                                if "analysis" in text_content or "success" in text_content:
                                                    logger.info(
                                                        "[v12] SUCCESS: Direct dict from tool_response.output[].text"
                                                    )
                                                    return text_content

                                        # Check for "json" key (alternative format)
                                        if "json" in output_item:
                                            inner = output_item["json"]
                                            if isinstance(inner, dict):
                                                if "analysis" in inner or "success" in inner:
                                                    logger.info(
                                                        "[v12] SUCCESS: Extracted from tool_response.output[].json"
                                                    )
                                                    return inner

                    # =====================================================
                    # v14 FIX: Handle direct "text" key in content_block
                    # CloudWatch showed: content_block = {"text": "{'success': ...}"}
                    # This format appears when tool returns simple text response
                    # Session: sga-session-8374a4b38be146daaee6092e0ccbd408
                    # =====================================================
                    if "text" in content_block and len(content_block) == 1:
                        text_content = content_block["text"]
                        logger.info(
                            "[v14] Found direct text block (no other keys), length=%d",
                            len(text_content) if text_content else 0,
                        )

                        if isinstance(text_content, str):
                            # Try JSON first (double quotes)
                            try:
                                parsed = json.loads(text_content)
                                # v16 DEBUG: Log what we parsed to understand wrapper format
                                logger.info(
                                    "[v16] v14 parsed JSON successfully, type=%s, keys=%s",
                                    type(parsed).__name__,
                                    list(parsed.keys())[:5] if isinstance(parsed, dict) else "N/A",
                                )
                                if isinstance(parsed, dict):
                                    if "analysis" in parsed or "success" in parsed:
                                        logger.info("[v14] SUCCESS: Parsed JSON from direct text block")
                                        return parsed
                                    # v16 FIX: Log any tool response wrappers found
                                    for key in parsed.keys():
                                        if key.endswith("_response"):
                                            logger.info("[v16] Found tool wrapper in text block: %s", key)
                                    # Also check for _response wrapper
                                    from_wrapper = _extract_from_response_wrapper(parsed)
                                    if from_wrapper:
                                        logger.info("[v14] SUCCESS: Extracted _response from direct text block")
                                        return from_wrapper
                            except json.JSONDecodeError as e:
                                # v16 DEBUG: Log parse failure details
                                logger.warning(
                                    "[v16] v14 JSON parse FAILED: %s (first 200 chars: %s)",
                                    str(e),
                                    text_content[:200] if text_content else "EMPTY",
                                )
                                # Python repr with single quotes - use ast.literal_eval
                                try:
                                    parsed = ast.literal_eval(text_content)
                                    if isinstance(parsed, dict):
                                        if "analysis" in parsed or "success" in parsed:
                                            logger.info("[v14] SUCCESS: Parsed Python repr from direct text block")
                                            return parsed
                                        from_wrapper = _extract_from_response_wrapper(parsed)
                                        if from_wrapper:
                                            logger.info("[v14] SUCCESS: Extracted _response from repr text block")
                                            return from_wrapper
                                except (ValueError, SyntaxError) as e:
                                    logger.debug("[v14] ast.literal_eval failed: %s", e)

                        elif isinstance(text_content, dict):
                            if "analysis" in text_content or "success" in text_content:
                                logger.info("[v14] SUCCESS: Direct dict in text block")
                                return text_content

                    # =====================================================
                    # KEEP legacy patterns as fallback (backward compatibility)
                    # =====================================================

                    # Legacy: "type": "tool_result" format (v10 code - may still work for some edge cases)
                    if content_block.get("type") == "tool_result":
                        tool_content = content_block.get("content", "")
                        logger.info("[v11] Found legacy tool_result block (type key)")
                        if isinstance(tool_content, str):
                            try:
                                parsed = json.loads(tool_content)
                                if isinstance(parsed, dict):
                                    if "analysis" in parsed or "success" in parsed:
                                        logger.info("[v13] SUCCESS: Direct from legacy tool_result")
                                        return parsed
                                    # v13 FIX: Check for _response wrapper BEFORE _unwrap_tool_result
                                    # This is the CRITICAL path for NEXO Smart Import!
                                    from_wrapper = _extract_from_response_wrapper(parsed)
                                    if from_wrapper:
                                        logger.info("[v13] SUCCESS: Extracted _response from legacy tool_result")
                                        return from_wrapper
                                    unwrapped = _unwrap_tool_result(parsed)
                                    if unwrapped:
                                        return unwrapped
                            except json.JSONDecodeError:
                                pass
                        elif isinstance(tool_content, dict):
                            if "analysis" in tool_content or "success" in tool_content:
                                return tool_content
                            # v13 FIX: Check for _response wrapper BEFORE _unwrap_tool_result
                            from_wrapper = _extract_from_response_wrapper(tool_content)
                            if from_wrapper:
                                return from_wrapper
                            unwrapped = _unwrap_tool_result(tool_content)
                            if unwrapped:
                                return unwrapped

                    # Direct json key in content block
                    if "json" in content_block:
                        inner = content_block["json"]
                        if isinstance(inner, dict) and (
                            "analysis" in inner or "success" in inner
                        ):
                            logger.info("[v11] SUCCESS: Extracted from dict.content[].json")
                            return inner

        # Fallback: Try standard unwrap (for non-Message dicts)
        unwrapped = _unwrap_tool_result(message)
        if unwrapped:
            logger.info("[v11] Extracted from direct dict message")
            return unwrapped

    return None


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

    # Priority 3: v13 FIX - Check for _response wrapper as last resort
    # This provides automatic coverage for ALL code paths that call _unwrap_tool_result()
    from_wrapper = _extract_from_response_wrapper(data)
    if from_wrapper:
        logger.info("[v13] Extracted from _response wrapper via _unwrap_tool_result")
        return from_wrapper

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
    Extract structured data from a single agent's result (AgentResult object).

    BUG-020 v8 FIX: Priority order for extraction:
    1. AgentResult.result.message (v8 - CORRECT path for AgentResult containing AgentResult)
    2. AgentResult.message (v8 - CORRECT path for direct AgentResult)
    3. AgentResult.result as dict (fallback for tools returning raw dicts)
    4. ToolResult format unwrapping (handles BUG-015 format)

    Official Strands AgentResult structure:
    - .message → Contains tool output (JSON string or Message object)
    - .stop_reason, .metrics, .state → Metadata (not useful for extraction)
    - .structured_output → May contain Pydantic model (rarely used)
    """
    # BUG-020 v8: Enhanced diagnostic logging
    logger.info(
        "[_extract_agent] agent=%s, has_result=%s, has_message=%s, result_type=%s",
        agent_name,
        hasattr(agent_result, "result"),
        hasattr(agent_result, "message"),
        type(agent_result.result).__name__ if hasattr(agent_result, "result") and agent_result.result else "None",
    )

    # =========================================================================
    # BUG-020 v8 FIX: Priority 1 — Extract from .message attribute
    # =========================================================================
    # CloudWatch logs revealed: AgentResult has .message, NOT nested .result!
    # The .message attribute contains tool output as JSON string.
    # =========================================================================

    # Priority 1a: Check if agent_result.result is an AgentResult with .message
    if hasattr(agent_result, "result") and agent_result.result:
        inner_result = agent_result.result

        # If inner_result is an AgentResult (has .message), extract from it
        if hasattr(inner_result, "message") and inner_result.message:
            logger.info(
                "[_extract_agent] v8: inner_result has .message, attempting extraction"
            )
            extracted = _extract_from_agent_message(inner_result.message)
            if extracted:
                logger.info(
                    "[_extract_agent] v8: SUCCESS from inner_result.message for agent=%s",
                    agent_name,
                )
                return extracted

    # Priority 1b: Check if agent_result itself has .message
    if hasattr(agent_result, "message") and agent_result.message:
        logger.info(
            "[_extract_agent] v8: agent_result has .message, attempting extraction"
        )
        extracted = _extract_from_agent_message(agent_result.message)
        if extracted:
            logger.info(
                "[_extract_agent] v8: SUCCESS from agent_result.message for agent=%s",
                agent_name,
            )
            return extracted

    # =========================================================================
    # Priority 2: Fallback to .result as dict (for tools returning raw dicts)
    # =========================================================================

    if not hasattr(agent_result, "result") or not agent_result.result:
        logger.warning("[_extract_agent] agent=%s has NO result attribute!", agent_name)
        return None

    result_data = agent_result.result

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

    # =========================================================================
    # BUG-020 v16 FIX: Handle nested AgentResult recursively
    # =========================================================================
    # Strands Swarm may return nested AgentResult structures:
    # result.results["agent"] = AgentResult where .result is ANOTHER AgentResult
    # When this happens, we need to recursively extract from the inner AgentResult.
    # =========================================================================
    if hasattr(result_data, "result") or hasattr(result_data, "message"):
        logger.info(
            "[v16] result_data is AgentResult (nested), type=%s, recursively extracting",
            type(result_data).__name__,
        )
        nested_extraction = _extract_from_agent_result(result_data, agent_name + "_nested", "unified_analyze_file")
        if nested_extraction:
            logger.info("[v16] SUCCESS: Extracted from nested AgentResult for agent=%s", agent_name)
            return nested_extraction

    # If result_data is not a dict at this point, we can't extract
    if not isinstance(result_data, dict):
        # Log available attributes for debugging
        logger.warning(
            "[_extract_agent] agent=%s result_data is NOT a dict! type=%s, attrs=%s",
            agent_name,
            type(result_data).__name__,
            [a for a in dir(result_data) if not a.startswith("_")][:10] if hasattr(result_data, "__dir__") else "N/A",
        )
        return None

    # =========================================================================
    # Priority 3: Unwrap ToolResult format (handles BUG-015 format)
    # =========================================================================

    unwrapped = _unwrap_tool_result(result_data)
    if unwrapped:
        logger.debug(
            "[_extract] Found valid result from agent %s via unwrap",
            agent_name,
        )
        return unwrapped

    # =========================================================================
    # Priority 4: Text content in ToolResult format
    # =========================================================================

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
