# Orchestrator Architecture (Strands Agent)

> **Last Updated:** 2026-01-14
> **Status:** Production
> **Pattern:** BedrockAgentCoreApp + Strands Agent (LLM-based routing)

This document describes the orchestrator architecture for Faiston One Inventory Management System (SGA).

---

## Overview

The orchestrator is the **central entry point** for all inventory management requests. It uses a **Strands Agent** with **Gemini 2.5 Flash** for intelligent routing to 14 specialist agents.

### Key Metrics

| Metric | Before | After |
|--------|--------|-------|
| Lines of Code | 4,426 | ~490 |
| HTTP Handlers | 75 | 1 |
| Routing Logic | Manual (if/else) | LLM-based |
| Extensibility | Code change required | System prompt only |

---

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRANDS ORCHESTRATOR PATTERN                             │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    BedrockAgentCoreApp                              │   │
│   │                    (HTTP /invocations - port 8080)                  │   │
│   │                                                                     │   │
│   │   @app.entrypoint                                                   │   │
│   │   def invoke(payload, context):                                     │   │
│   │       return orchestrator(prompt)  # LLM decides routing            │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    Strands Agent                                    │   │
│   │                    name="FaistonInventoryManagement"                │   │
│   │                                                                     │   │
│   │   model: Gemini 2.5 Flash (fast routing decisions)                 │   │
│   │   tools: [invoke_specialist, health_check]                         │   │
│   │   system_prompt: "Route to appropriate specialist..."               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    invoke_specialist Tool                           │   │
│   │                    @tool                                            │   │
│   │                    async def invoke_specialist(                     │   │
│   │                        agent_id: str,                               │   │
│   │                        action: str,                                 │   │
│   │                        payload: dict                                │   │
│   │                    ) -> dict                                        │   │
│   │                                                                     │   │
│   │   Uses A2AClient to invoke specialists via JSON-RPC 2.0            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. BedrockAgentCoreApp

The official SDK for deploying agents to AWS Bedrock AgentCore.

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: dict, context) -> dict:
    # Single entry point for all requests
    ...
```

### 2. Strands Agent

The LLM-based router that understands user intent.

```python
from strands import Agent

orchestrator = Agent(
    name="FaistonInventoryManagement",
    model=create_gemini_model("orchestrator"),  # Gemini 2.5 Flash
    tools=[invoke_specialist, health_check],
    system_prompt=SYSTEM_PROMPT,
)
```

### 3. invoke_specialist Tool

The primary routing mechanism using A2A Protocol.

```python
@tool
async def invoke_specialist(
    agent_id: str,
    action: str,
    payload: dict,
    session_id: str = None,
) -> dict:
    """Invoke a specialist agent via A2A Protocol (JSON-RPC 2.0)."""
    client = _get_a2a_client()
    result = await client.invoke_agent(agent_id, payload, session_id)
    return {"success": True, "specialist_agent": agent_id, "response": result}
```

---

## Routing Logic

The LLM (Gemini Flash) reads the system prompt and decides which specialist to invoke:

| User Intent | Specialist | Action |
|-------------|-----------|--------|
| "Analyze this inventory file" | nexo_import | analyze_file |
| "Process this Nota Fiscal PDF" | intake | process_nf |
| "Check stock balance for C9200-24P" | estoque_control | query_balance |
| "Create a reservation" | estoque_control | create_reservation |
| "Start inventory count" | reconciliacao | start_campaign |
| "Get shipping quotes" | carrier | get_quotes |

### System Prompt (Excerpt)

```markdown
## Available Specialist Agents

| Agent ID | Capabilities | When to Use |
|----------|-------------|-------------|
| estoque_control | Reservations, expeditions, transfers, returns | Stock movements |
| intake | NF PDF/XML extraction and processing | Document intake |
| nexo_import | Smart file import with AI analysis | File analysis, data import |
| learning | Prior knowledge retrieval, pattern learning | Historical patterns |
| validation | Data and schema validation | Data quality checks |
| reconciliacao | Inventory counts, divergence analysis | Physical counting |
| compliance | Policy validation, approval workflows | HIL tasks, approvals |
| carrier | Shipping quotes, carrier recommendation | Logistics, shipping |
| expedition | Expedition processing, stock verification | Outbound logistics |
| reverse | Return processing, condition evaluation | Reverse logistics |
| observation | Audit logging, import analysis | Observations, audit |
| schema_evolution | Column type inference, schema changes | Schema analysis |
| equipment_research | Equipment documentation research | Equipment specs |
| data_import | Generic data import operations | Bulk imports |
```

---

## Backward Compatibility

For existing frontend code that uses direct action names, a mapping table provides backward compatibility:

```python
ACTION_TO_SPECIALIST = {
    # EstoqueControl
    "where_is_serial": ("estoque_control", "query_asset_location"),
    "get_balance": ("estoque_control", "query_balance"),
    "create_reservation": ("estoque_control", "create_reservation"),

    # Intake
    "process_nf_upload": ("intake", "process_nf"),
    "process_image_ocr": ("intake", "parse_nf_image"),

    # NexoImport
    "nexo_analyze_file": ("nexo_import", "analyze_file"),
    "nexo_submit_answers": ("nexo_import", "submit_answers"),

    # ... 40+ more mappings
}
```

When `payload.action` is provided, the orchestrator bypasses LLM routing and directly invokes the mapped specialist.

---

## Request Modes

### Mode 1: Health Check

```json
{"action": "health_check"}
```

Returns system status, version, deployed commit, and available specialists.

### Mode 2: Direct Action (Backward Compatibility)

```json
{
  "action": "nexo_analyze_file",
  "file_path": "s3://bucket/inventory.csv",
  "session_id": "session-123"
}
```

Uses `ACTION_TO_SPECIALIST` mapping to route directly.

### Mode 3: Natural Language (LLM Routing)

```json
{
  "prompt": "Analyze this inventory file and identify unmapped columns",
  "session_id": "session-123"
}
```

The Strands Agent (Gemini) interprets intent and calls `invoke_specialist`.

---

## Code Location

| File | Purpose |
|------|---------|
| `server/agentcore-inventory/main.py` | Orchestrator entry point (~610 lines with Phase 7.1) |
| `server/agentcore-inventory/main.py.backup` | Original 75-handler version (4,426 lines) |
| `server/agentcore-inventory/agents/utils.py` | `create_gemini_model()` factory |
| `server/agentcore-inventory/shared/a2a_client.py` | A2A Protocol client |
| `server/agentcore-inventory/shared/a2a_tool_provider.py` | **NEW** Dynamic agent discovery (Phase 7.1) |

---

## Phase 7.1: Dynamic Agent Discovery

> **Added:** 2026-01-14
> **Status:** Implemented (feature flag disabled by default)

### A2AToolProvider

The `A2AToolProvider` class implements dynamic agent discovery via A2A Protocol:

```python
from shared.a2a_tool_provider import A2AToolProvider

# Create provider and discover agents
provider = A2AToolProvider()
await provider.discover_all_agents()

# Use discovered agents with Strands Agent
orchestrator = Agent(
    tools=provider.tools,
    system_prompt=provider.build_system_prompt(),
)
```

### Feature Flag

Enable dynamic discovery via environment variable:

```bash
export USE_DYNAMIC_DISCOVERY=true
```

When enabled:
1. AgentCards fetched from `/.well-known/agent-card.json` at startup
2. System prompt generated from discovered skills
3. Action mapping built from AgentCard skills

When disabled (default):
- Static system prompt with hardcoded agent list
- Static `ACTION_TO_SPECIALIST` mapping for backward compatibility

### Discovery Flow

```
┌─────────────────────────────────────────────────────────────┐
│                A2A DYNAMIC DISCOVERY                         │
│                                                             │
│  Startup:                                                   │
│  1. A2AToolProvider iterates RUNTIME_IDS                    │
│  2. Fetches AgentCard from each: /.well-known/agent-card.json│
│  3. Extracts skills, capabilities, descriptions             │
│  4. Builds dynamic system prompt                            │
│  5. Creates action mapping from skills                      │
│                                                             │
│  Runtime:                                                   │
│  - LLM routes based on discovered capabilities              │
│  - Direct actions map to discovered skills                  │
│  - Fallback to static mapping if discovery fails            │
└─────────────────────────────────────────────────────────────┘
```

### Benefits

| Feature | Static (Current) | Dynamic (Phase 7.1) |
|---------|-----------------|---------------------|
| New Agent | Code change required | Auto-discovered |
| System Prompt | Manual update | Generated from skills |
| Action Mapping | Hardcoded | Built from AgentCard |
| Skill Changes | Code change | Reflected automatically |

---

## Phase 7.2: ToolContext for Clean State Management

> **Added:** 2026-01-14
> **Status:** Implemented

### Problem: State Management Without Polluting LLM Context

Before Phase 7.2, user context (user_id, session_id) was either:
1. Passed in the prompt text (polluting LLM context window)
2. Hardcoded or extracted inconsistently

### Solution: Strands ToolContext with invocation_state

The Strands SDK provides `ToolContext` for accessing state that is:
- **Hidden from the LLM** (not part of the prompt)
- **Available to tools** (passed via invocation_state)
- **Traceable** (toolUseId for request correlation)

### Implementation Pattern

```python
from strands import tool, ToolContext

@tool(context=True)  # Enable ToolContext injection
async def invoke_specialist(
    agent_id: str,
    action: str,
    payload: dict,
    tool_context: ToolContext,  # Injected by Strands
) -> dict:
    # Access hidden state (NOT visible to LLM)
    user_id = tool_context.invocation_state.get("user_id", "unknown")
    session_id = tool_context.invocation_state.get("session_id", "default-session")
    request_id = tool_context.tool_use.get("toolUseId", "unknown")

    # Use context in tool logic...
```

### Invocation Pattern

```python
# When calling the Agent, pass invocation_state as kwargs
result = orchestrator(
    "Route this request to the appropriate specialist",
    user_id=user_id,       # Hidden from LLM
    session_id=session_id,  # Hidden from LLM
    debug=False,            # Hidden from LLM
)
```

### Architecture: Internal Helper Function

Phase 7.2 introduced a separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    TOOL LAYER                                │
│                                                             │
│  @tool(context=True)                                        │
│  invoke_specialist()                                        │
│    - Extracts context from ToolContext.invocation_state    │
│    - Delegates to internal function                         │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  _invoke_specialist_internal()                              │
│    - Core A2A invocation logic                             │
│    - Used by both @tool and direct action routing          │
│    - No dependency on ToolContext                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Benefits

| Feature | Before Phase 7.2 | After Phase 7.2 |
|---------|------------------|-----------------|
| User context in LLM | In prompt (pollutes context) | Hidden in invocation_state |
| Request tracing | Manual/inconsistent | toolUseId automatic |
| Direct action routing | Shared code with tool | Separate internal function |
| Debug information | Hardcoded | Configurable via state |

### Code Location

| File | Purpose |
|------|---------|
| `main.py:233-278` | Internal helper function `_invoke_specialist_internal()` |
| `main.py:280-337` | Tool-decorated `invoke_specialist()` with ToolContext |
| `main.py:580-585` | Orchestrator invocation with invocation_state |

---

## Future Architecture: 100% Swarm

> **Decision (2026-01-14):** The next phase will transform the orchestrator into a **100% Swarm architecture** with Meta-Tooling for self-improvement.

### Swarm vs Current Architecture

| Aspect | Current (Agents-as-Tools) | Future (Swarm) |
|--------|--------------------------|----------------|
| Routing | LLM calls `invoke_specialist` tool | Agents autonomously hand off |
| Control | Centralized (orchestrator decides) | Decentralized (agents decide) |
| Self-Improvement | No | Yes (Meta-Tooling) |
| Performance | Fast (single LLM call) | Slower (~2x) but more autonomous |

See: `docs/plans/swift-finding-dongarra.md` for full Swarm architecture plan.

---

## Related Documentation

- [SMART_IMPORT_ARCHITECTURE.md](./SMART_IMPORT_ARCHITECTURE.md) - Import flow details
- [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) - Auth configuration
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
