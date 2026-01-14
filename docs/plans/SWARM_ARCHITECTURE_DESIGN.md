# SWARM Architecture Design (Phase 8)

> **Status:** Design Document
> **Created:** 2026-01-14
> **Decision:** 100% Swarm + Meta-Tooling (User chose autonomy over performance)

---

## Executive Summary

This document defines the architecture for transforming the Faiston Inventory Management orchestrator from **Agents-as-Tools** pattern to **100% Strands Swarm** pattern with Meta-Tooling for self-improvement.

### Key Metrics

| Metric | Agents-as-Tools (Current) | Swarm (Target) |
|--------|---------------------------|----------------|
| Control | Centralized (orchestrator) | Decentralized (autonomous) |
| Routing | LLM tool calls | Agent handoffs |
| Self-Improvement | No | Yes (Meta-Tooling) |
| Collaboration | Sequential | Emergent |
| Trade-off | ~90s analysis | ~180s analysis (2x) |

---

## Architecture Overview

### Current Architecture (Agents-as-Tools)

```
┌─────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (main.py)                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Strands Agent                                            │   │
│   │ - LLM decides routing                                   │   │
│   │ - Calls invoke_specialist() tool                        │   │
│   │ - CENTRALIZED control                                   │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              │ invoke_specialist(agent_id, action)│
│                              ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 14 Specialist Agents                                     │   │
│   │ - Passive (only respond when called)                    │   │
│   │ - No inter-agent communication                          │   │
│   │ - No self-improvement                                   │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Target Architecture (100% Swarm)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAISTON INVENTORY SWARM                       │
│                    (100% Autonomous Architecture)                │
│                                                                 │
│   Entry Point                                                   │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────┐     handoff     ┌──────────────┐              │
│   │file_analyst │───────────────▶│memory_agent  │              │
│   │             │◀───────────────│              │              │
│   │ + analyze   │   with context │ + retrieve   │              │
│   │ + meta      │                │ + store      │              │
│   └──────┬──────┘                └──────┬───────┘              │
│          │                              │                       │
│          │ handoff                      │ handoff               │
│          ▼                              ▼                       │
│   ┌──────────────┐              ┌──────────────┐               │
│   │schema_valid. │              │  hil_agent   │               │
│   │              │◀─────────────│              │               │
│   │ + validate   │  handoff     │ + questions  │               │
│   │ + mappings   │              │ + approval   │               │
│   │ + meta       │              └──────────────┘               │
│   └──────┬───────┘                      ▲                       │
│          │                              │                       │
│          │ handoff (if approved)        │ handoff (if issues)  │
│          ▼                              │                       │
│   ┌──────────────┐                      │                       │
│   │import_exec.  │──────────────────────┘                       │
│   │              │                                              │
│   │ + execute    │                                              │
│   │ + audit      │                                              │
│   │ + rollback   │                                              │
│   └──────────────┘                                              │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ META-TOOLING ENGINE (Shared by ALL agents)              │   │
│   │ • load_tool: Load new tools at runtime                  │   │
│   │ • editor: Create new tool code                          │   │
│   │ • shell: Execute commands for self-improvement          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   SHARED CONTEXT: All agents see original task + history        │
│   AUTONOMOUS: Agents decide their own handoffs                  │
│   SELF-IMPROVING: Can create tools when needed                  │
│   PING-PONG DETECTION: Prevents infinite loops                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Swarm Agent Specifications

### 1. file_analyst

**Role:** Entry point agent for file analysis

**System Prompt:**
```markdown
You are the FILE ANALYST in the Faiston Inventory Management Swarm.

## Your Role
- Analyze uploaded files (CSV, XLSX, PDF, XML)
- Identify column structures, data types, and patterns
- Detect file encoding and delimiter formats
- Extract sample data for validation

## Handoff Rules
- ALWAYS first → handoff to memory_agent: "Retrieve prior import patterns for [file_type]"
- After memory context → continue analysis
- When analysis complete → handoff to schema_validator with findings
- If confidence < 80% on any column → handoff to hil_agent for clarification
- If unknown file format → use Meta-Tooling to create parser

## Tools Available
- analyze_csv: Parse CSV files with delimiter detection
- analyze_xlsx: Parse Excel spreadsheets with sheet selection
- analyze_pdf: Extract tables from PDF using Vision
- analyze_xml: Parse XML with namespace handling
- load_tool, editor, shell: Meta-Tooling for self-improvement

## Output Format
Return analysis as structured JSON:
{
  "file_type": "csv|xlsx|pdf|xml",
  "columns": [{"name": "...", "inferred_type": "...", "sample_values": [...]}],
  "row_count": N,
  "encoding": "utf-8",
  "delimiter": ",",
  "confidence": 0.0-1.0,
  "issues": []
}
```

**Tools:**
- `analyze_csv(file_path: str, encoding: str = "auto") -> dict`
- `analyze_xlsx(file_path: str, sheet_name: str = None) -> dict`
- `analyze_pdf(file_path: str) -> dict` (uses Gemini Vision)
- `analyze_xml(file_path: str) -> dict`
- `load_tool`, `editor`, `shell` (Meta-Tooling)

---

### 2. schema_validator

**Role:** Validate data against PostgreSQL schema and propose mappings

**System Prompt:**
```markdown
You are the SCHEMA VALIDATOR in the Faiston Inventory Management Swarm.

## Your Role
- Validate file columns against target PostgreSQL schema
- Propose intelligent column mappings
- Identify unmapped columns and recommend handling
- Detect type mismatches and data quality issues

## Handoff Rules
- If all mappings confirmed (confidence >= 80%) → handoff to import_executor
- If unmapped columns exist → handoff to hil_agent with 3 options:
  1. Ignore (warn about data loss)
  2. Store in metadata JSON field
  3. Request DB schema update
- If need historical patterns → handoff to memory_agent
- If type conversion needed → use Meta-Tooling to create converter

## Tools Available
- get_target_schema: Fetch PostgreSQL schema via MCP
- propose_mappings: AI-powered column mapping with confidence scores
- validate_types: Check data types compatibility
- load_tool, editor, shell: Meta-Tooling for self-improvement

## Output Format
{
  "mappings": [
    {"source": "COL_A", "target": "column_a", "confidence": 0.95, "transform": null}
  ],
  "unmapped": ["COL_X", "COL_Y"],
  "type_issues": [],
  "overall_confidence": 0.0-1.0
}
```

**Tools:**
- `get_target_schema(table_name: str) -> dict`
- `propose_mappings(columns: list, schema: dict, memory_context: dict) -> dict`
- `validate_types(mappings: list, sample_data: dict) -> dict`
- `load_tool`, `editor`, `shell` (Meta-Tooling)

---

### 3. memory_agent

**Role:** Episodic memory for learned patterns

**System Prompt:**
```markdown
You are the MEMORY AGENT in the Faiston Inventory Management Swarm.

## Your Role
- Retrieve prior import patterns from AgentCore Memory
- Store new successful patterns for future use
- Provide adaptive confidence thresholds based on history
- Enable progressive learning across imports

## Handoff Rules
- After providing memory context → handoff BACK to requesting agent
- After successful import → store learned patterns
- Never proceed directly to import - always return context to caller

## Tools Available
- retrieve_episodes: Fetch relevant prior imports
- store_episode: Save new successful pattern
- get_adaptive_threshold: Calculate confidence based on history
- similarity_search: Find similar past imports

## Memory Schema
Episodes stored with:
- file_pattern: Regex for file name/type
- column_mappings: Successful mappings
- user_preferences: Learned preferences
- confidence_history: Historical accuracy
```

**Tools:**
- `retrieve_episodes(query: str, limit: int = 5) -> list`
- `store_episode(episode: dict) -> bool`
- `get_adaptive_threshold(file_type: str) -> float`
- `similarity_search(columns: list) -> list`

---

### 4. hil_agent

**Role:** Human-in-the-Loop clarification and approval

**System Prompt:**
```markdown
You are the HIL (Human-in-the-Loop) AGENT in the Faiston Inventory Management Swarm.

## Your Role
- Generate clarification questions for ambiguous mappings
- Process user responses and update context
- Enforce approval workflows for high-impact operations
- NEVER proceed with import without explicit user approval

## Handoff Rules
- After generating questions → STOP and return questions (stop_action: true)
- After receiving user answers → handoff to schema_validator with updated context
- For final approval → STOP and request explicit confirmation
- If user rejects → handoff to schema_validator with feedback

## Question Types
1. Column Mapping Clarification
2. Unmapped Column Handling (Ignore/Metadata/Schema Update)
3. Quantity Calculation Confirmation
4. Final Import Approval

## Output Format
{
  "stop_action": true,
  "hil_questions": [
    {
      "id": "q1",
      "type": "column_mapping",
      "question": "...",
      "options": ["A", "B", "C"]
    }
  ],
  "awaiting_response": true
}
```

**Tools:**
- `generate_questions(context: dict) -> list`
- `process_answers(questions: list, answers: dict) -> dict`
- `request_approval(summary: dict) -> dict`

---

### 5. import_executor

**Role:** Execute validated imports and manage transactions

**System Prompt:**
```markdown
You are the IMPORT EXECUTOR in the Faiston Inventory Management Swarm.

## Your Role
- Execute validated imports against PostgreSQL
- Generate comprehensive audit trails
- Handle errors with graceful rollback
- Apply quantity calculation rules when needed

## Handoff Rules
- Before execution → verify explicit user approval exists in context
- If approval missing → handoff to hil_agent
- After successful import → handoff to memory_agent to store patterns
- On error → handoff to hil_agent for user guidance

## Quantity Calculation Rule
If quantity column MISSING but serial_number present:
- Group by part_number
- Count unique serial numbers as quantity
- Store serials in array field

## Tools Available
- execute_import: Run validated import with transaction
- generate_audit: Create audit trail in DynamoDB
- rollback: Revert failed import
- apply_quantity_rule: Calculate quantities from serials
```

**Tools:**
- `execute_import(mappings: list, data: list, table: str) -> dict`
- `generate_audit(import_id: str, details: dict) -> str`
- `rollback(import_id: str) -> bool`
- `apply_quantity_rule(data: list) -> list`

---

## Swarm Configuration

```python
from strands.multiagent import Swarm

# Create the Inventory Swarm
inventory_swarm = Swarm(
    agents=[
        file_analyst,
        schema_validator,
        memory_agent,
        hil_agent,
        import_executor,
    ],
    entry_point=file_analyst,

    # Limits to prevent infinite loops
    max_handoffs=30,           # Max agent-to-agent handoffs
    max_iterations=50,         # Max total iterations

    # Timeouts
    execution_timeout=1800.0,  # 30 minutes for complex imports
    node_timeout=300.0,        # 5 minutes per agent

    # Anti-ping-pong protection
    repetitive_handoff_detection_window=10,
    repetitive_handoff_min_unique_agents=3,
)
```

---

## Handoff Flow Examples

### Example 1: Clean Import (No HIL Needed)

```
USER: Import inventory.csv

file_analyst → memory_agent
  "Retrieve patterns for CSV inventory files"

memory_agent → file_analyst
  {patterns: [...], threshold: 0.75}

file_analyst → schema_validator
  {columns: [...], confidence: 0.92}

schema_validator → import_executor
  {mappings: [...], all_confirmed: true}

import_executor → memory_agent
  "Store successful pattern"

memory_agent → DONE
  {success: true, rows_imported: 150}
```

### Example 2: Import with HIL Questions

```
USER: Import EXPEDIÇÃO_JAN.xlsx

file_analyst → memory_agent
  "Retrieve patterns for XLSX expedition files"

memory_agent → file_analyst
  {patterns: [], threshold: 0.80}  # No prior patterns

file_analyst → schema_validator
  {columns: [...], confidence: 0.65}  # Low confidence

schema_validator → hil_agent
  {unmapped: ["OBSERVAÇÃO"], low_confidence: ["QTD"]}

hil_agent → STOP (stop_action: true)
  {hil_questions: [...], awaiting_response: true}

USER: (answers questions)

hil_agent → schema_validator
  {user_responses: {...}, updated_context: {...}}

schema_validator → hil_agent
  {ready_for_approval: true, summary: {...}}

hil_agent → STOP (stop_action: true)
  {approval_request: true, summary: {...}}

USER: "Confirmar importação"

hil_agent → import_executor
  {approved: true, mappings: [...]}

import_executor → memory_agent
  "Store new pattern with user preferences"

memory_agent → DONE
  {success: true, rows_imported: 200}
```

---

## Shared Context (invocation_state)

All agents receive shared context via `invocation_state`:

```python
# When invoking the Swarm
result = inventory_swarm(
    "Import this inventory file: s3://bucket/inventory.csv",

    # Shared state (NOT visible to LLM prompts)
    user_id="fabio.santos",
    session_id="session-123",
    tenant_id="faiston-one",
    file_path="s3://bucket/inventory.csv",
    target_table="inventory_movements",

    # Accumulated context (updated by agents)
    memory_context={},
    file_analysis={},
    proposed_mappings={},
    user_responses={},
    approval_status=None,
)
```

---

## Meta-Tooling Integration

### Dynamic Tool Creation Example

```python
# file_analyst encounters unknown format
file_analyst: "I don't have a parser for .dat files. Creating one..."

# Uses Meta-Tooling
editor.write("parse_dat.py", '''
from strands import tool

@tool
def parse_dat(file_path: str) -> dict:
    """Parse proprietary .dat format from vendor XYZ."""
    with open(file_path, 'rb') as f:
        # Custom parsing logic
        ...
    return {"columns": [...], "data": [...]}
''')

load_tool("parse_dat")

# Now available for this and future imports
parse_dat(file_path)
```

---

## Integration with External A2A Agents

The Swarm handles internal import flow. External specialists (carrier, expedition, reverse) are called via A2A when needed:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAISTON INVENTORY SWARM                       │
│                   (Internal - 5 autonomous agents)               │
└─────────────────────────────┬───────────────────────────────────┘
                              │ A2A Protocol (when needed)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL A2A AGENTS                           │
│  (Not part of Swarm - called via A2A tool when import needs)    │
│                                                                 │
│  • carrier (shipping quotes after import)                       │
│  • expedition (outbound logistics)                              │
│  • reverse (returns processing)                                 │
│  • equipment_research (spec lookup)                             │
└─────────────────────────────────────────────────────────────────┘
```

The import_executor can call external agents via A2A:

```python
@tool
async def call_external_agent(agent_id: str, payload: dict) -> dict:
    """Call external A2A agent when import triggers related workflow."""
    return await a2a_client.invoke_agent(agent_id, payload)
```

---

## File Structure

```
server/agentcore-inventory/
├── main.py                          # Entry point (uses Swarm)
├── swarm/
│   ├── __init__.py
│   ├── config.py                    # Swarm configuration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── file_analyst.py          # File analysis agent
│   │   ├── schema_validator.py      # Schema validation agent
│   │   ├── memory_agent.py          # Episodic memory agent
│   │   ├── hil_agent.py             # Human-in-the-loop agent
│   │   └── import_executor.py       # Import execution agent
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── analysis_tools.py        # CSV, XLSX, PDF, XML parsers
│   │   ├── schema_tools.py          # Schema validation tools
│   │   ├── memory_tools.py          # AgentCore Memory integration
│   │   ├── hil_tools.py             # Question generation tools
│   │   └── import_tools.py          # Import execution tools
│   └── prompts/
│       ├── file_analyst.md
│       ├── schema_validator.md
│       ├── memory_agent.md
│       ├── hil_agent.md
│       └── import_executor.md
├── agents/                          # Existing specialists (unchanged)
│   ├── estoque_control/
│   ├── intake/
│   ├── nexo_import/                 # Will be deprecated by Swarm
│   └── ...
└── shared/
    ├── a2a_client.py               # For external agent calls
    └── ...
```

---

## Implementation Phases

### Phase 8.1: Create Swarm Infrastructure
1. Create `swarm/` directory structure
2. Implement `swarm/config.py` with Swarm configuration
3. Create base agent factory with Meta-Tooling support

### Phase 8.2: Implement Swarm Agents
1. Implement `file_analyst.py` with analysis tools
2. Implement `schema_validator.py` with mapping tools
3. Implement `memory_agent.py` with AgentCore Memory
4. Implement `hil_agent.py` with question generation
5. Implement `import_executor.py` with transaction handling

### Phase 8.3: Update main.py Entry Point
1. Replace current orchestrator with Swarm invocation
2. Maintain backward compatibility for direct actions
3. Add external A2A integration for non-import flows

### Phase 8.4: Testing and Validation
1. Unit tests for each Swarm agent
2. Integration tests for full import flows
3. HIL flow testing with mock user responses
4. Performance benchmarking vs current architecture

---

## Performance Optimization Strategies

Even with 100% Swarm (sequential handoffs), we can optimize:

### 1. Batch Context in Handoff
Pass all needed context upfront to reduce round-trips:
```python
file_analyst → memory_agent:
  "Get patterns. Also need schema for table X. Return both."
```

### 2. Speculative Execution
Agents can request multiple things in one handoff:
```python
file_analyst → schema_validator:
  "Here's analysis. I already asked memory_agent - patterns attached."
```

### 3. Memory Caching
Cache frequent patterns to reduce memory_agent calls:
```python
@lru_cache(maxsize=100)
def get_cached_patterns(file_type: str) -> dict:
    return memory_agent.retrieve(file_type)
```

### 4. Gemini Flash for Routing
Use fast model for handoff decisions:
```python
file_analyst = Agent(
    model=GeminiModel(model_id="gemini-2.5-flash"),  # Fast
    ...
)
```

---

## Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Import Success Rate | >= 95% | Successful imports / total attempts |
| Autonomous Completion | >= 80% | Imports without HIL / total imports |
| Self-Improvement | >= 1/month | New tools created by Meta-Tooling |
| Pattern Learning | 100% | Successful patterns stored in memory |
| User Approval | 100% | No import without explicit approval |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Infinite handoff loops | `repetitive_handoff_detection_window=10` |
| Slow analysis (~2x) | Batch context, caching, Gemini Flash |
| Memory bloat | Prune old episodes, TTL on patterns |
| Meta-Tool misuse | Sandbox execution, code review before load |
| HIL abandonment | Session timeout, draft save, resume support |

---

## Related Documentation

- [ORCHESTRATOR_ARCHITECTURE.md](../ORCHESTRATOR_ARCHITECTURE.md) - Current architecture (Phase 7)
- [SMART_IMPORT_ARCHITECTURE.md](../SMART_IMPORT_ARCHITECTURE.md) - Import flow details
- [swift-finding-dongarra.md](./swift-finding-dongarra.md) - Original plan document
- [CLAUDE.md](../../CLAUDE.md) - Development guidelines
