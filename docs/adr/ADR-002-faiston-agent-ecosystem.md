# ADR-002: Faiston Agent Ecosystem Architecture

## Status

**Accepted** (2026-01-14)

## Context

The current SGA (Sistema de Gestão de Ativos) architecture has the orchestrator (`main.py`) implemented as a **Python wrapper** that manually routes requests to specialist agents. This violates the core principle that **"Everything is an Agent"** in an AI-first platform.

### Current Problems

1. **Orchestrator is NOT a Strands Agent**
   - `main.py` is a procedural Python file that wraps agent calls
   - Routing logic is hardcoded in system prompts (decision trees)
   - Does not use Strands Agent features (hooks, session management, structured output)

2. **Specialists are Nested Under Orchestrator**
   - Directory structure implies specialists "belong to" orchestrator
   - Violates reusability principle (specialists should serve ANY orchestrator)

3. **Custom A2A Implementation (Redundant)**
   - `shared/a2a_client.py` duplicates official `a2a.client` functionality
   - `shared/a2a_tool_provider.py` reimplements Strands patterns

4. **Missing Strands Features**
   - No `AgentCoreMemorySessionManager` for long-term memory
   - No `HookProvider` implementations (logging, metrics, guardrails)
   - No `structured_output_model` for typed responses
   - No `Swarm` integration for NEXO multi-agent workflows

### Relevant Documentation (Source of Truth)

- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/agent-loop/
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/
- https://strandsagents.com/latest/documentation/docs/community/session-managers/agentcore-memory/

## Decision

### 1. "Everything is an Agent" Principle

The orchestrator MUST be a full **Strands Agent**, not a Python wrapper:

```python
from strands import Agent
from strands.multiagent.a2a import A2AServer

orchestrator = Agent(
    name="FaistonInventoryOrchestrator",
    model=create_gemini_model("orchestrator"),
    system_prompt=SYSTEM_PROMPT,  # NO routing tables
    tools=create_specialist_tools(),
    session_manager=create_session_manager(session_id, actor_id),
    hooks=[LoggingHook(), MetricsHook()]
)
```

### 2. New Directory Structure

Orchestrators and specialists at the **SAME LEVEL**:

```
server/agentcore-inventory/
├── agents/
│   ├── orchestrators/           # Domain orchestrators
│   │   ├── estoque/             # 📦 Inventory (current)
│   │   ├── expedicao/           # 🚚 Expedition (future)
│   │   ├── reversa/             # 🔄 Reverse logistics (future)
│   │   └── rastreabilidade/     # 🔍 Traceability (future)
│   │
│   └── specialists/             # Reusable capabilities
│       ├── estoque_control/
│       ├── intake/
│       ├── nexo_import/
│       ├── learning/
│       ├── validation/
│       ├── reconciliacao/
│       ├── compliance/
│       ├── carrier/
│       ├── expedition/
│       ├── reverse/
│       ├── observation/
│       ├── schema_evolution/
│       ├── equipment_research/
│       ├── data_import/
│       └── enrichment/
│
├── shared/
│   ├── models.py                # Gemini model factory
│   ├── memory.py                # AgentCore Memory config
│   └── hooks/
│       ├── logging_hook.py
│       ├── metrics_hook.py
│       └── guardrails_hook.py
│
└── config/
    └── agent_urls.py            # Runtime ID → URL mapping
```

### 3. Use Official A2A Client

Replace custom implementation with official `a2a.client`:

```python
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart

class A2ASpecialistTool:
    """Wraps an A2A agent as a Strands tool."""

    async def _ensure_client(self):
        resolver = A2ACardResolver(httpx_client=self._httpx_client, base_url=self.agent_url)
        self._agent_card = await resolver.get_agent_card()
        config = ClientConfig(httpx_client=self._httpx_client, streaming=True)
        factory = ClientFactory(config)
        self._client = factory.create(self._agent_card)
```

### 4. No Routing Tables in Prompts

System prompt MUST NOT contain routing logic:

```python
# ❌ WRONG - Hardcoded routing
SYSTEM_PROMPT = """
If request is about inventory → invoke estoque_control
If request is about import → invoke nexo_import
...
"""

# ✅ CORRECT - LLM decides based on tool descriptions
SYSTEM_PROMPT = """
You are the Faiston Inventory Management Orchestrator.
Your role is to understand user requests and delegate to appropriate specialists.
You have access to specialist agents via tools.
Let the tools describe themselves.
"""
```

### 5. Full Strands Feature Utilization

Every agent MUST implement:

| Feature | Implementation |
|---------|----------------|
| Agent Loop | Automatic via `Agent` class |
| State Management | `agent.state.get/set` |
| Session Memory | `AgentCoreMemorySessionManager` |
| Hooks | `LoggingHook`, `MetricsHook` |
| Structured Output | `Pydantic` models |
| Async Streaming | `agent.stream_async()` |
| A2A Server | `A2AServer` for each agent |
| Swarm | Integrated in orchestrator for NEXO |

### 6. Breaking Change (No Backward Compatibility)

Remove all legacy code:
- `shared/a2a_client.py` → DELETE
- `shared/a2a_tool_provider.py` → DELETE
- Old `main.py` routing patterns → REWRITE

## Consequences

### Positive

- **Clean Architecture**: Orchestrators and specialists at same level
- **Reusability**: Any orchestrator can use any specialist
- **Future-Proof**: Easy to add new domain orchestrators
- **Full Strands Integration**: All framework features utilized
- **AGI-like Behavior**: Proper OBSERVE → THINK → LEARN → ACT loop
- **Memory Persistence**: AgentCore Memory for learning loops

### Negative

- **Breaking Change**: All deployments need update
- **Migration Effort**: ~6-8 days of implementation
- **Terraform Updates**: New paths require IaC changes

### Mitigation

- Deploy in waves: specialists first, then orchestrator
- Use feature flags if needed during transition
- Comprehensive testing before production

## Alternatives Considered

### 1. Keep Current Structure, Add Features

- **Rejected**: Would perpetuate "wrapper" anti-pattern
- Doesn't solve "orchestrator is not an agent" problem

### 2. Gradual Migration with Backward Compatibility

- **Rejected**: User explicitly chose "REMOVER (breaking change)"
- Simplifies code, forces clean architecture

### 3. Separate Repository for Orchestrators

- **Rejected**: Over-engineering for current scale
- All agents benefit from shared utilities

## Related

- **ADR-001**: Remove Orphan Dockerfiles ✅
- **CLAUDE.md**: AI-First Platform Identity
- **docs/ORCHESTRATOR_ARCHITECTURE.md**: Technical details
- **docs/SMART_IMPORT_ARCHITECTURE.md**: NEXO Swarm integration

## Implementation Plan

| Phase | Duration | Description |
|-------|----------|-------------|
| 1 | 1 day | Restructure directories |
| 2 | 2-3 days | Rewrite orchestrator as Strands Agent |
| 3 | 1-2 days | Update specialists with full features |
| 4 | 1 day | Integrate Swarm for NEXO |
| 5 | 1 day | Deploy and verification |

## Notes

This decision aligns with CLAUDE.md principles:
- "FAISTON ONE is a 100% AUTONOMOUS and GENERATIVE AI agent system"
- "This is a 100% AI-FIRST and AGENTIC platform"
- "ALL agents MUST use AWS STRANDS AGENTS FRAMEWORK"
- "NEXO BEHAVIOR (MANDATORY): The NEXO agent MUST behave in an AGI-like manner"
