---
paths:
  - "**/nexo*.py"
  - "**/nexo*.ts"
  - "**/inventory*.py"
  - "**/import*.py"
  - "**/sga*.py"
  - "server/agents/**/nexo*"
  - "server/agents/**/inventory*"
---

# NEXO Agent — AGI-Like Behavior Rules

> See `docs/SMART_IMPORT_ARCHITECTURE.md` for complete flow diagrams, runtime IDs, and code locations.

## Authentication Protocol Architecture

```
Frontend (JWT) → faiston_asset_management (HTTP) → faiston_sga_* (A2A/SigV4)
```

- **NEVER** call `faiston_sga_*` agents directly from frontend
- Frontend MUST call `faiston_asset_management-uSuLPsFQNH` (HTTP orchestrator)
- Orchestrator routes to specialist agents via A2A protocol
- Calling A2A agent with JWT → "Empty response payload" (auth mismatch)

## Core Principle: Multi-Round Iterative HIL Dialogue

- Agent MUST engage in **ITERATIVE conversation** with user (NOT one-shot)
- Each user response triggers **RE-ANALYSIS** by Gemini with FULL context
- Loop continues until **ALL mappings** have confidence >= 80%
- **NEVER** proceed to import without final user **EXPLICIT APPROVAL**

## Context Sent to Gemini (EVERY ROUND)

1. **File Content** — CSV/XLSX/PDF data (sample or full)
2. **Memory Context** — Prior learned patterns from LearningAgent (AgentCore Memory)
3. **Schema Context** — PostgreSQL target schema (columns, types, constraints)
4. **User Responses** — Accumulated answers from HIL dialogue
5. **User Comments** — Free-text instructions/feedback

```
ROUND 1: Memory + File + Schema → Gemini → Questions
ROUND 2: Memory + File + Schema + User Responses → Gemini → More Questions or Ready
ROUND N: Memory + File + Schema + All Responses → Gemini → Final Mappings
```

## Unmapped Column Handling

Columns NOT in DB schema MUST be FLAGGED with 3 OPTIONS:
1. **Ignore** — Data NOT imported (warn about data loss)
2. **Store in metadata** — Preserve in JSON field (recommended)
3. **Request DB update** — Contact Faiston IT team

**BLOCKING:** Import BLOCKED until user decides on ALL unmapped columns

## Quantity Calculation Rule

If `quantity` missing but `serial_number` present:
- Group by `part_number`
- Count unique serial numbers as quantity
- Store serial numbers in array field
- Each `part_number` must be UNIQUE

## Final Summary Before Import

Present SUMMARY before executing:
- Total record count
- Column mappings (source → target)
- Ignored fields
- Warnings/issues
- Unmapped columns decision recap

**REQUIRE explicit approval** ("Confirmar importação?")

## Learning Loop

After successful import, STORE learned patterns:
- Column naming patterns
- User preferences
- File format patterns

## Enforcement

- ONE-SHOT analysis (no re-analysis after user response) → **WRONG**
- Proceeding without explicit approval → **WRONG**
- Ignoring unmapped columns without asking → **WRONG**
- Not storing learned patterns → **WRONG**
