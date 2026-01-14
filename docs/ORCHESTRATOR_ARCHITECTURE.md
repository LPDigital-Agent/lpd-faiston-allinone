# Orchestrator Architecture (Strands Agent)

> **Last Updated:** 2026-01-14
> **Status:** Production (Phase 2 of ADR-002 Migration Complete)
> **Pattern:** BedrockAgentCoreApp + Full Strands Agent (LLM-based routing)
> **ADR Reference:** [ADR-002 - Faiston Agent Ecosystem Architecture](./adr/ADR-002-faiston-agent-ecosystem.md)

This document describes the orchestrator architecture for Faiston One Inventory Management System (SGA).

---

## ADR-002: "Everything is an Agent" Architecture

> **Principle:** The orchestrator IS a Strands Agent, NOT a Python wrapper.

Per ADR-002 (Accepted 2026-01-14), the architecture follows these principles:

1. **Orchestrators are Agents** - Full Strands Agent with hooks, session management, structured output
2. **Specialists at Same Level** - All agents (orchestrators and specialists) are peers, not parent-child
3. **Multiple Orchestrators Supported** - Future domain orchestrators (expedicao, reversa, rastreabilidade)
4. **No Routing Tables in Prompts** - LLM decides routing based on tool descriptions

### New Directory Structure (Phase 2 Complete)

```
server/agentcore-inventory/agents/
├── orchestrators/           # Domain orchestrators (full Strands Agents)
│   └── estoque/             # 📦 Inventory management
│       ├── __init__.py
│       └── main.py          # ✅ Phase 2 - Full Strands Agent (~790 lines)
└── specialists/             # Reusable capabilities (15 agents)
    ├── estoque_control/
    ├── intake/
    ├── nexo_import/
    └── ... (12 more)
```

---

## Overview

The orchestrator is the **central entry point** for all inventory management requests. It uses a **Strands Agent** with **Gemini 2.5 Flash** for intelligent routing to 15 specialist agents.

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

## Routing Architecture (ADR-002 Compliant)

> **Updated:** 2026-01-14 (ADR-002 Phase 2 + BUG-017 Fix)

Per ADR-002, the old `ACTION_TO_SPECIALIST` mapping was **removed** (breaking change). The new routing architecture maintains **100% Agentic AI** for business logic:

### Routing Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ROUTING DECISION TREE                                │
│                                                                             │
│   Request (action or prompt)                                                │
│            │                                                                │
│            ├── action == "health_check" ?                                   │
│            │        │                                                       │
│            │        YES → Mode 1: Direct health response                    │
│            │                                                                │
│            ├── action in SWARM_ACTIONS ?                                    │
│            │        │                                                       │
│            │        YES → Mode 2: Autonomous 5-agent Swarm                  │
│            │                                                                │
│            ├── action in INFRASTRUCTURE_ACTIONS ?                           │
│            │        │                                                       │
│            │        YES → Mode 2.5: Deterministic routing (S3 only)         │
│            │                                                                │
│            └── else                                                         │
│                     │                                                       │
│                     └── Mode 3: LLM-based routing (100% Agentic)            │
│                          - Natural language → Gemini reasoning              │
│                          - Business data → Gemini → A2A → MCP → DB          │
│                          - Unknown actions → Gemini decides specialist      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Goes Where

| Category | Mode | LLM Used? | Example |
|----------|------|-----------|---------|
| Health Check | 1 | ❌ No | `{"action": "health_check"}` |
| NEXO Import | 2 | ❌ (Swarm) | `{"action": "nexo_analyze_file", ...}` |
| S3 URLs | 2.5 | ❌ No | `{"action": "get_nf_upload_url", ...}` |
| Business Data | 3 | ✅ Yes | `{"prompt": "Get balance for C9200-24P"}` |
| Natural Language | 3 | ✅ Yes | `{"prompt": "Where is serial TSP001?"}` |

### Why Mode 2.5 Exists

BUG-017 (2026-01-14): The ADR-002 migration removed `ACTION_TO_SPECIALIST` which broke S3 upload URLs. Mode 2.5 restores **deterministic routing for infrastructure operations only**, while preserving the 100% Agentic AI principle for all business logic.

---

## Request Modes

### Mode 1: Health Check

```json
{"action": "health_check"}
```

Returns system status, version, deployed commit, and available specialists.

### Mode 2: Swarm Routing (NEXO Imports)

```json
{
  "action": "nexo_analyze_file",
  "file_path": "s3://bucket/inventory.csv",
  "session_id": "session-123"
}
```

Actions in `SWARM_ACTIONS` (nexo_*) are routed to the autonomous 5-agent Swarm for intelligent file import processing.

### Mode 2.5: Infrastructure Actions (Direct Tool Call)

> **Added:** 2026-01-14 (BUG-017 Fix)
> **Updated:** 2026-01-14 (BUG-017 v2 - Direct tool call, no A2A)

```json
{
  "action": "get_nf_upload_url",
  "filename": "inventory.csv",
  "content_type": "text/csv"
}
```

**IMPORTANT:** This mode is ONLY for pure infrastructure operations (S3 presigned URLs, etc.) that:
- Do NOT require LLM reasoning
- Do NOT involve business data
- ARE pure technical operations

**BUG-017 Root Cause & Fix:**
- **Problem:** Initial fix used A2A protocol which passes through specialist's LLM, wrapping JSON in conversational text
- **Fix:** Direct import of `SGAS3Client` in orchestrator - calls tool functions directly without A2A
- **Result:** Raw JSON response (`{upload_url, s3_key}`) returned to frontend without LLM wrapping

```python
INFRASTRUCTURE_ACTIONS = {
    "get_nf_upload_url": ("intake", "get_upload_url"),
    "get_presigned_download_url": ("intake", "get_download_url"),
}

def _handle_infrastructure_action(action, payload):
    """Direct tool call - bypasses A2A entirely."""
    from tools.s3_client import SGAS3Client
    s3 = SGAS3Client()
    # ... direct S3 operations
```

**100% Agentic AI Principle:** ALL business data queries (query_balance, query_asset_location, etc.) MUST go through Mode 3 (LLM routing). Only pure infrastructure operations can use Mode 2.5.

### Mode 3: Natural Language (LLM Routing)

```json
{
  "prompt": "Analyze this inventory file and identify unmapped columns",
  "session_id": "session-123"
}
```

The Strands Agent (Gemini) interprets intent and calls `invoke_specialist`.

**This mode handles:**
- Natural language requests
- Business data queries (query_balance, query_asset_location)
- All operations NOT in SWARM_ACTIONS or INFRASTRUCTURE_ACTIONS

---

## Code Location

### Legacy Location (Pre-ADR-002 Migration)

| File | Purpose | Status |
|------|---------|--------|
| `server/agentcore-inventory/main.py` | Re-export wrapper (now thin proxy) | ✅ Updated |
| `server/agentcore-inventory/main.py.backup` | Original 75-handler version (4,426 lines) | 📁 Archive |
| `server/agentcore-inventory/shared/a2a_client.py` | A2A Protocol client for specialists (~1,185 lines) | ✅ Kept (used by specialists) |
| `server/agentcore-inventory/shared/a2a_tool_provider.py` | Dynamic agent discovery (~506 lines) | 🗑️ Removed (orchestrator only) |

> **Note:** `a2a_client.py` is KEPT because specialists use `delegate_to_*` functions for inter-specialist communication (e.g., nexo_import → learning). The orchestrator no longer uses this file - it has inline boto3 SDK calls.

### New Location (ADR-002 Phase 2 Complete)

| File | Purpose |
|------|---------|
| `server/agentcore-inventory/agents/orchestrators/estoque/main.py` | **Full Strands Agent orchestrator (~790 lines)** |
| `server/agentcore-inventory/agents/specialists/` | All 15 specialist agents |
| `server/agentcore-inventory/config/agent_urls.py` | Runtime ID → URL mapping (source of truth) |
| `server/agentcore-inventory/agents/utils.py` | `create_gemini_model()` factory |
| `server/agentcore-inventory/shared/hooks/` | HookProvider implementations |
| `server/agentcore-inventory/shared/hooks/logging_hook.py` | JSON structured logging |
| `server/agentcore-inventory/shared/hooks/metrics_hook.py` | CloudWatch metrics emission |
| `server/agentcore-inventory/shared/hooks/guardrails_hook.py` | Shadow mode content moderation |

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

---

## ADR-002 Migration Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Complete | Restructure directories (orchestrators/ + specialists/) |
| **Phase 2** | ✅ Complete | Rewrite orchestrator as full Strands Agent (~790 lines) |
| **Phase 3** | ✅ Complete | Update specialists with AgentCoreMemory, hooks |
| **Phase 4** | ✅ Complete | Integrate Swarm for NEXO (embedded in orchestrator) |
| **Phase 5** | Pending | Deploy and verification |

---

## Phase 2 Implementation Details

> **Added:** 2026-01-14
> **Status:** Complete
> **File:** `server/agentcore-inventory/agents/orchestrators/estoque/main.py`

### Key Changes from Legacy Orchestrator

| Aspect | Legacy (`main.py`) | New (`orchestrators/estoque/main.py`) |
|--------|-------------------|---------------------------------------|
| Lines of Code | ~1,318 | ~790 |
| Routing Tables | Hardcoded in SYSTEM_PROMPT | None - LLM reads tool descriptions |
| A2A Implementation | Custom `shared/a2a_client.py` | Direct boto3 SDK calls |
| Agent Discovery | `shared/a2a_tool_provider.py` | Removed - static RUNTIME_IDS |
| Backward Compatibility | ACTION_TO_SPECIALIST mapping | Removed (breaking change per ADR-002) |
| Swarm Integration | External module | Embedded in orchestrator |

### LLM-Based Routing Pattern

The new orchestrator removes all routing tables from the system prompt. Instead, the LLM reads the `invoke_specialist` tool docstring which contains detailed agent descriptions:

```python
@tool(context=True)
async def invoke_specialist(agent_id: str, action: str, payload: dict, tool_context: ToolContext) -> dict:
    """
    ## Available Specialist Agents:

    ### estoque_control
    Inventory control operations: stock movements, reservations...
    Actions: query_balance, create_reservation, cancel_reservation...

    ### intake
    Document intake and processing: NF PDF/XML extraction...
    Actions: process_nf, validate_extraction, confirm_entry...

    ... (15 agents total)
    """
```

### invocation_state for Hidden Context

User and session context is passed via `invocation_state` (invisible to LLM):

```python
# In entrypoint
result = orchestrator(
    llm_prompt,
    user_id=user_id,       # Hidden from LLM
    session_id=session_id,  # Hidden from LLM
)

# In tool (accessed via ToolContext)
user_id = tool_context.invocation_state.get("user_id", "unknown")
session_id = tool_context.invocation_state.get("session_id", "default-session")
```

### A2A Invocation via boto3 SDK

The new orchestrator uses boto3 directly (no custom wrapper):

```python
client = boto3.client("bedrock-agentcore", region_name="us-east-2")
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps(a2a_request).encode("utf-8"),
)
```

### Hooks Integration

The orchestrator uses HookProvider implementations:

1. **LoggingHook** - JSON structured logging for all agent events
2. **MetricsHook** - CloudWatch metrics emission (FaistonSGA namespace)
3. **GuardrailsHook** - Shadow mode content moderation (optional)

```python
hooks = [
    LoggingHook(log_level=logging.INFO),
    MetricsHook(namespace="FaistonSGA", emit_to_cloudwatch=True),
]
if guardrail_id:
    hooks.append(GuardrailsHook(guardrail_id=guardrail_id, shadow_mode=True))
```

---

## Phase 3 Implementation Details

> **Added:** 2026-01-14
> **Status:** Complete
> **Files:** All 15 specialist agents in `server/agentcore-inventory/agents/specialists/`

### Summary

All 15 specialist agents have been updated to include HookProvider implementations for observability per ADR-002. This ensures consistent logging and metrics across the entire agent ecosystem.

### Updated Specialists

| Specialist | Role | Hooks Added |
|------------|------|-------------|
| estoque_control | Stock management | LoggingHook, MetricsHook |
| intake | Inventory entry | LoggingHook, MetricsHook |
| nexo_import | Smart import | LoggingHook, MetricsHook |
| learning | Pattern learning | LoggingHook, MetricsHook |
| validation | Data validation | LoggingHook, MetricsHook |
| compliance | Compliance checks | LoggingHook, MetricsHook |
| carrier | Carrier management | LoggingHook, MetricsHook |
| data_import | Data import | LoggingHook, MetricsHook |
| equipment_research | Equipment research | LoggingHook, MetricsHook |
| expedition | Expedition management | LoggingHook, MetricsHook |
| observation | Audit logging | LoggingHook, MetricsHook |
| reconciliacao | Reconciliation | LoggingHook, MetricsHook |
| reverse | Reverse logistics | LoggingHook, MetricsHook |
| schema_evolution | Dynamic schema | LoggingHook, MetricsHook |
| nf_reader | NF parsing | LoggingHook, MetricsHook |

### Standard Pattern Applied

Each specialist received the same hook integration pattern:

```python
# Import hooks
from shared.hooks import LoggingHook, MetricsHook

# Apply in create_agent()
def create_agent() -> Agent:
    return Agent(
        name=AGENT_NAME,
        model=create_gemini_model(AGENT_ID),
        tools=[...],
        system_prompt=SYSTEM_PROMPT,
        hooks=[LoggingHook(), MetricsHook()],  # ADR-002: Observability hooks
    )
```

### Benefits

1. **Consistent Logging**: All agents emit JSON-structured logs to CloudWatch
2. **Metrics Visibility**: CloudWatch metrics track invocations, duration, tool usage
3. **Debugging**: Easier to trace issues across multi-agent workflows
4. **Compliance**: Audit trail for all agent operations

---

## Related Documentation

- [ADR-002 - Faiston Agent Ecosystem Architecture](./adr/ADR-002-faiston-agent-ecosystem.md) - "Everything is an Agent" decision
- [ADR-001 - Remove Orphan Dockerfiles](./adr/ADR-001-remove-orphan-dockerfiles.md) - ZIP deploy decision
- [SMART_IMPORT_ARCHITECTURE.md](./SMART_IMPORT_ARCHITECTURE.md) - Import flow details
- [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md) - Auth configuration
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
