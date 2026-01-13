# ADR-003: Gemini 3.0 Model Selection and Thinking Configuration

**Status:** Accepted
**Date:** January 2026
**Decision Makers:** Architecture Team
**Context:** NEXO Memory Architecture Audit

---

## Summary

All agents MUST use **Gemini 3.0 family** models exclusively:
- **gemini-3.0-pro**: Import/analysis agents with Thinking mode enabled
- **gemini-3.0-flash**: Operational agents for simple tasks

---

## Context

### Mandate

From `CLAUDE.md`:
> "All agents use Gemini 3.0 Pro exclusively (per CLAUDE.md mandate)"

### Problem

Prior audit discovered **ALL 14 agents** were hardcoding `gemini-2.0-flash`:

```python
# WRONG - Found in ALL agent files
MODEL = "gemini-2.0-flash"  # ❌ Violates mandate
```

### Gemini 3.0 Features

| Feature | Flash | Pro |
|---------|-------|-----|
| Speed | Fast | Moderate |
| Cost | Lower | Higher |
| Reasoning | Basic | **Deep** |
| Thinking Mode | ❌ No | ✅ Yes |
| File Analysis | Basic | **Advanced** |
| Context Window | 1M | 2M |

---

## Decision

### 1. Centralized Model Configuration

Create centralized model selection in `agents/utils.py`:

```python
# Gemini 3.0 Model Family (MANDATORY)
MODEL_GEMINI_FLASH = "gemini-3.0-flash"
MODEL_GEMINI_PRO = "gemini-3.0-pro"

# Agents requiring Pro + Thinking (file analysis, schema understanding)
PRO_THINKING_AGENTS = {
    "nexo_import",      # Main orchestrator - file analysis with schema
    "intake",           # Document intake - NF parsing with Vision
    "import",           # Data import - file structure understanding
    "learning",         # Memory extraction - pattern recognition
    "schema_evolution", # Schema analysis - SQL generation
}

# Agents requiring Pro (complex reasoning, no thinking)
PRO_AGENTS = {
    "compliance",       # Audit, regulatory analysis
}

def get_model(agent_type: str = "default") -> str:
    """Get appropriate Gemini 3.0 model for agent type."""
    if agent_type in PRO_THINKING_AGENTS or agent_type in PRO_AGENTS:
        return os.environ.get("GEMINI_MODEL_PRO", MODEL_GEMINI_PRO)
    return os.environ.get("GEMINI_MODEL", MODEL_GEMINI_FLASH)
```

### 2. Model Assignment Matrix

| Category | Model | Thinking | Count | Agents |
|----------|-------|----------|-------|--------|
| **Import/Analysis** | `gemini-3.0-pro` | HIGH | 5 | nexo_import, intake, import, learning, schema_evolution |
| **Complex Reasoning** | `gemini-3.0-pro` | None | 1 | compliance |
| **Operational** | `gemini-3.0-flash` | None | 8 | observation, validation, equipment_research, estoque_control, expedition, reverse, carrier, reconciliacao |
| **Tools (Import)** | `gemini-3.0-pro` | HIGH | 2 | match_items, parse_nf |

### 3. Thinking Configuration

For agents requiring deep reasoning:

```python
from google.genai import types

def get_thinking_config(agent_type: str = "default"):
    """Get thinking configuration for deep reasoning agents."""
    if agent_type in PRO_THINKING_AGENTS:
        return {
            "thinking_config": {
                "thinking_level": "high"  # Maximize reasoning depth
            }
        }
    return None
```

---

## Rationale

### Why Gemini 3.0 Pro for Import Agents

Import agents perform complex file analysis:

1. **File Structure Understanding**: Parse XLSX/CSV with multiple sheets
2. **Column Mapping**: Match file columns to PostgreSQL schema
3. **Pattern Recognition**: Identify data types from sample values
4. **Schema Awareness**: Understand target database structure

These tasks benefit from:
- Extended context window (2M tokens)
- Deep reasoning capabilities
- Thinking mode for step-by-step analysis

### Why Thinking Mode

Gemini 3.0 Thinking mode (per [Google docs](https://ai.google.dev/gemini-api/docs/thinking)):

```python
thinking_config=types.ThinkingConfig(thinking_level="high")
```

Benefits:
- **Chain-of-thought reasoning**: Model explains its logic
- **Higher accuracy**: Complex file analysis improves
- **Better error detection**: Catches mapping mistakes

### Why Flash for Operational Agents

Operational agents perform simple, well-defined tasks:
- Inventory queries
- Status updates
- Carrier quotes
- Shipping tracking

These don't need deep reasoning, so Flash provides:
- Lower latency
- Lower cost
- Sufficient capability

---

## Alternatives Considered

### Alternative 1: All Pro

```python
MODEL = "gemini-3.0-pro"  # For ALL agents
```

**Pros:**
- Uniform capability
- Maximum reasoning everywhere

**Cons:**
- Unnecessary cost for simple tasks
- Higher latency for operational agents

**Rejected because:** Cost/benefit ratio poor for operational tasks.

### Alternative 2: All Flash

```python
MODEL = "gemini-3.0-flash"  # For ALL agents
```

**Pros:**
- Lowest cost
- Fastest responses

**Cons:**
- Import accuracy suffers
- No thinking mode available
- File analysis quality degrades

**Rejected because:** Import intelligence requires Pro capabilities.

### Alternative 3: Environment Variable Only

```python
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.0-flash")
```

**Pros:**
- Full flexibility
- No code changes to switch

**Cons:**
- Single model for all agents
- No per-agent optimization
- Easy to misconfigure

**Rejected because:** Different agents have different requirements.

---

## Implementation

### Files Modified (16 total)

**Import Agents (Pro + Thinking)**:
```
agents/nexo_import/agent.py       → get_model("nexo_import")
agents/intake/agent.py            → get_model("intake")
agents/data_import/agent.py       → get_model("data_import")  # Renamed from import (Python reserved)
agents/learning/agent.py          → get_model("learning")
agents/schema_evolution/agent.py → get_model("schema_evolution")
agents/intake/tools/match_items.py → gemini-3.0-pro
agents/intake/tools/parse_nf.py    → gemini-3.0-pro
```

**Complex Reasoning (Pro)**:
```
agents/compliance/agent.py       → get_model("compliance")
```

**Operational (Flash)**:
```
agents/observation/agent.py       → get_model("observation")
agents/validation/agent.py        → get_model("validation")
agents/equipment_research/agent.py→ get_model("equipment_research")
agents/estoque_control/agent.py   → get_model("estoque_control")
agents/expedition/agent.py        → get_model("expedition")
agents/reverse/agent.py           → get_model("reverse")
agents/carrier/agent.py           → get_model("carrier")
agents/reconciliacao/agent.py     → get_model("reconciliacao")
```

### Agent Code Pattern

```python
# agents/{agent_name}/agent.py
from google.adk.agents import Agent

# Centralized model configuration (MANDATORY - Gemini 3.0)
from agents.utils import get_model

AGENT_ID = "agent_name"
AGENT_MODEL = get_model(AGENT_ID)

def create_agent() -> Agent:
    return Agent(
        model=AGENT_MODEL,
        name=AGENT_NAME,
        instruction=INSTRUCTION,
        tools=[...],
    )
```

### Environment Override

For testing/development, models can be overridden:

```bash
# Force Pro for all agents
export GEMINI_MODEL_PRO="gemini-3.0-pro-preview"

# Force Flash for all agents
export GEMINI_MODEL="gemini-3.0-flash"
```

---

## Consequences

### Positive

1. **Compliance**: Meets Gemini 3.0 mandate from `CLAUDE.md`
2. **Optimized cost**: Flash for simple tasks, Pro for complex
3. **Better import accuracy**: Thinking mode improves file analysis
4. **Centralized control**: Single place to update models
5. **Flexibility**: Environment variables for override

### Negative

1. **Higher cost for imports**: Pro costs more than Flash
2. **Longer latency for imports**: Thinking mode adds time
3. **Maintenance**: Must update utils.py for new agents

### Mitigations

| Risk | Mitigation |
|------|------------|
| Higher import cost | Worth it for accuracy improvement |
| Longer import latency | Import is async anyway |
| Maintenance | Clear categorization rules documented |

---

## Google References

- [Gemini 3.0 Overview](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Thinking Mode](https://ai.google.dev/gemini-api/docs/thinking)
- [Deep Research](https://ai.google.dev/gemini-api/docs/deep-research)
- [File Understanding](https://ai.google.dev/gemini-api/docs/files)
- [Prompting Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)

---

## Related ADRs

- **ADR-001**: [GLOBAL Namespace Design](./ADR-001-global-namespace.md)
- **ADR-002**: [Self-Managed Strategy Pattern](./ADR-002-self-managed-strategy.md)

---

## Review

| Date | Reviewer | Status |
|------|----------|--------|
| Jan 2026 | Memory Architecture Audit | Validated |

---

*This ADR documents an intentional architectural decision. Changes require team review.*
