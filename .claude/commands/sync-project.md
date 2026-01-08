## Phase 4: UPDATE CLAUDE.md (REQUIRED)

**File**: `CLAUDE.md` (root)

### 4.0 Non-Negotiable Rule (MANDATORY)
NEVER REMOVE OR REPLACE items marked with:
- `## DO NOT REMOVE`
- `### Important (Never Change or replace it)`
- IMMUTABLE BLOCK markers/comments

### 4.1 What is Allowed to Update in ROOT CLAUDE.md

Allowed updates are ONLY:
- New global policies (stable, short, universal)
- Corrections to typos/formatting that do NOT change meaning
- Links to new docs (do NOT paste long content)

NOT allowed in root CLAUDE.md:
- Long inventories (routes, components, endpoints)
- “Known Issues & Fixes” logs
- Sprint notes, changelogs, migrations
- Anything that changes frequently

### 4.2 Where to Put Non-Policy Content

- Routes/pages/components/endpoints → `docs/PROJECT_STATE.md`
- Known issues & fixes → `docs/KNOWN_ISSUES.md`
- UI patterns / design system deltas → `docs/DESIGN_SYSTEM.md`
- Module-level specifics:
  - frontend → `client/CLAUDE.md`
  - AgentCore runtimes → `server/<agentcore-module>/CLAUDE.md`
  - Terraform/IaC → `terraform/CLAUDE.md`

### 4.3 Execute Update

Use the `Edit` tool for precise, minimal changes. Do NOT rewrite the entire file.
