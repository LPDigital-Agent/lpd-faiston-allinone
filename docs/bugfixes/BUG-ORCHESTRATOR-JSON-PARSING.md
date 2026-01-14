# BUG: Orchestrator JSON Parsing Error

**Status**: FIXED
**Date**: 2026-01-14
**Branch**: carriers-integration
**Affected Runtime**: `faiston_asset_management_dev-r0YOohHtwd` (dev orchestrator)
**Commit**: 907cea3

---

## Problem Description

The dev orchestrator agent responded with HTTP 200 but had an application-level JSON parsing error when receiving natural language requests.

**Test Case**:
```json
{
  "prompt": "Get shipping quotes for a package"
}
```

**Expected Behavior**:
- Orchestrator routes request to carrier agent
- Carrier agent returns structured JSON with shipping quotes
- Orchestrator returns the response to user

**Actual Behavior**:
- Orchestrator LLM sometimes responded with natural language text
- Code tried to parse natural language as JSON: `json.loads(result.message)`
- JSON parsing failed → user received malformed response
- HTTP 200 returned but response was not valid JSON

---

## Root Cause Analysis

### Code Location
**File**: `server/agentcore-inventory/main.py`
**Function**: `invoke()` (lines 1126-1309)
**Mode**: Natural Language → LLM-based Routing (lines 1228-1261)

### Issue Flow

1. User sends `{"prompt": "Get shipping quotes..."}`
2. Orchestrator enters LLM routing mode (line 1228)
3. Creates/gets Strands Agent orchestrator (line 1232)
4. Calls `orchestrator(context_info, user_id=..., session_id=...)` (line 1240)
5. **PROBLEM**: LLM returns natural language instead of calling `invoke_specialist` tool
6. Code tries `json.loads(result.message)` (line 1250)
7. **FAILURE**: JSONDecodeError because message is plain text

### Why Did This Happen?

The system prompt said "Always return the specialist's response as-is in JSON format" but didn't ENFORCE tool usage. Gemini Flash sometimes interpreted this as "respond in JSON" rather than "call the tool".

---

## Solution

### Changes Made

**File**: `server/agentcore-inventory/main.py`

#### 1. Enhanced System Prompt (lines 71-159)

**Before**:
```python
DEFAULT_SYSTEM_PROMPT = """
## 🎯 You are Faiston Inventory Management Orchestrator

You are the central intelligence for the SGA...
Your role is to:
1. UNDERSTAND the user's intent
2. IDENTIFY which specialist agent should handle
3. INVOKE the appropriate specialist via the invoke_specialist tool
4. RETURN the specialist's response
...
"""
```

**After**:
```python
DEFAULT_SYSTEM_PROMPT = """
## 🎯 You are Faiston Inventory Management Orchestrator

## CRITICAL: Tool-Only Mode

YOU MUST ALWAYS use the invoke_specialist tool. NEVER respond directly with natural language.

Your workflow:
1. UNDERSTAND the user's intent from their message
2. IDENTIFY which specialist agent should handle the request
3. INVOKE the appropriate specialist via the invoke_specialist tool
4. The tool will return the specialist's response - pass it through as-is

...

## ⚠️ CRITICAL RULES

1. NEVER respond with natural language explanations
2. ALWAYS use the invoke_specialist tool - even for simple questions
3. The tool returns structured JSON - pass it through as-is
4. If the user request doesn't have structured data, pass the prompt in payload
...
"""
```

**Key Additions**:
- "CRITICAL: Tool-Only Mode" section at the top
- Explicit examples showing natural language routing
- "NEVER respond with natural language explanations"
- Clear rule: "ALWAYS use the invoke_specialist tool"

#### 2. Improved Response Extraction (lines 1259-1304)

**Before**:
```python
# Extract the response
if hasattr(result, "message"):
    try:
        return json.loads(result.message)
    except json.JSONDecodeError:
        return {
            "success": True,
            "response": result.message,
            "agent_id": AGENT_ID,
        }
return {
    "success": True,
    "response": str(result),
    "agent_id": AGENT_ID,
}
```

**After**:
```python
# Extract the response
# Priority 1: Try to get tool result (structured response from invoke_specialist)
if hasattr(result, "tool_results") and result.tool_results:
    # Tool was called - return the structured response
    tool_result = result.tool_results[0]
    if isinstance(tool_result, dict):
        return tool_result
    return {
        "success": True,
        "response": tool_result,
        "agent_id": AGENT_ID,
    }

# Priority 2: Try to parse message as JSON (if LLM returned JSON directly)
if hasattr(result, "message") and result.message:
    try:
        parsed = json.loads(result.message)
        # Ensure it looks like a specialist response
        if isinstance(parsed, dict) and "specialist_agent" in parsed:
            return parsed
        # Wrap it if it's just raw JSON
        return {
            "success": True,
            "response": parsed,
            "agent_id": AGENT_ID,
        }
    except json.JSONDecodeError:
        # Natural language response - this shouldn't happen with fixed prompt
        logger.warning(
            f"[Orchestrator] LLM returned natural language instead of using tools: {result.message[:200]}"
        )
        return {
            "success": False,
            "error": "Orchestrator failed to route request properly",
            "debug_message": result.message,
            "agent_id": AGENT_ID,
            "hint": "The orchestrator did not use the invoke_specialist tool. This is a configuration issue.",
        }

# Priority 3: Fallback - return string representation
return {
    "success": False,
    "error": "Unexpected response format from orchestrator",
    "response": str(result),
    "agent_id": AGENT_ID,
}
```

**Key Improvements**:
- 3-priority extraction system
- First tries `tool_results` (when tool was called)
- Diagnostic logging when tool wasn't used
- Clear error messages for debugging

---

## Testing

### Test Case 1: Natural Language Request
```bash
curl -X POST https://[orchestrator-endpoint]/invocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [JWT_TOKEN]" \
  -d '{"prompt": "Get shipping quotes for a package"}'
```

**Expected Response** (structured JSON):
```json
{
  "success": true,
  "specialist_agent": "carrier",
  "response": {
    "quotes": [...],
    "success": true
  },
  "request_id": "..."
}
```

### Test Case 2: Specific Request
```bash
curl -X POST https://[orchestrator-endpoint]/invocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [JWT_TOKEN]" \
  -d '{"prompt": "Get shipping quote from 01310-100 to 04567-000 for 5kg"}'
```

**Expected Response**:
- Orchestrator calls carrier agent
- Carrier agent extracts parameters from natural language
- Returns structured shipping quotes

### Test Case 3: Direct Action (Backward Compatibility)
```bash
curl -X POST https://[orchestrator-endpoint]/invocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [JWT_TOKEN]" \
  -d '{
    "action": "get_shipping_quotes",
    "origin_cep": "01310-100",
    "destination_cep": "04567-000",
    "weight_kg": 5.0
  }'
```

**Expected Behavior**:
- Should still work (backward compatibility maintained)
- Routes directly to carrier agent via action mapping

---

## Deployment Instructions

### Dev Environment
Deploy using GitHub Actions:
```bash
# Push to carriers-integration branch
git push origin carriers-integration

# Workflow will auto-deploy to dev environment
# Agent: faiston_asset_management_dev
# Runtime ID: r0YOohHtwd
```

### Production
After testing in dev:
```bash
# Merge to main
git checkout main
git merge carriers-integration
git push origin main

# Production workflow will deploy
# Agent: faiston_asset_management
# Runtime ID: uSuLPsFQNH
```

---

## Prevention

### For Future Prompts

When designing system prompts for orchestrator agents:

1. **Always enforce tool usage**: Add "CRITICAL: Tool-Only Mode" section
2. **Be explicit**: Say "NEVER respond with natural language"
3. **Provide examples**: Show concrete examples of tool calls
4. **Test with natural language**: Always test with ambiguous prompts

### Code Review Checklist

When reviewing orchestrator changes:

- [ ] System prompt enforces tool-only mode
- [ ] Response extraction handles all cases (tool results, JSON, natural language)
- [ ] Diagnostic logging is in place
- [ ] Error messages are clear and actionable
- [ ] Backward compatibility is maintained

---

## Monitoring

### CloudWatch Logs

Watch for these log patterns:

**Good** (tool was called):
```
[Orchestrator] LLM routing: Get shipping quotes...
[Orchestrator] Routing to specialist: carrier, action: handle_request
[A2A] Invoking carrier via boto3 SDK
[Orchestrator] Tool result extracted successfully
```

**Bad** (tool wasn't called):
```
[Orchestrator] LLM routing: Get shipping quotes...
[Orchestrator] LLM returned natural language instead of using tools: I'll help you...
```

If you see the "Bad" pattern:
1. Check if system prompt was overwritten during deployment
2. Verify Gemini model is configured correctly
3. Check if tools are registered properly with the Agent

---

## Related Issues

- **BUG-013**: JWT authorizer configuration
- **BUG-015**: Swarm response extraction (similar issue with tool results)
- **BUG-016**: JWT authorizer restoration after async deployment

---

## References

- **Strands Agents Documentation**: https://strandsagents.com/latest/
- **A2A Protocol**: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
- **Tool Calling**: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/
- **System Prompts**: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/

---

## Sign-off

**Fixed by**: Claude Code (2026-01-14)
**Reviewed by**: Pending
**Deployed to dev**: Pending
**Deployed to prod**: Pending

**Notes**:
- Fix is backward compatible
- No breaking changes
- System prompt enhancement
- Better error handling
- Improved observability
