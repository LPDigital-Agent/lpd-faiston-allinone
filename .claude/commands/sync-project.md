---
name: sync-project
description: Sync and update all project documentation, memory, and reference files to reflect current project state
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoRead, TodoWrite
hooks:
  Stop:
    - type: command
      command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/mark_sync_done.sh"
---

# Sync Project — Complete Project State Update

This command performs a comprehensive synchronization of project documentation, Claude Code commands, and MCP memory to reflect the current project state.

---

## Phase 1: Analyze Current Project State

### 1.1 Git Repository State

```bash
echo "=== GIT STATE ==="
echo "Branch: $(git branch --show-current)"
echo ""
echo "Uncommitted Changes:"
git status --short || true
echo ""
echo "Recent Commits (Last 10):"
git log --oneline -10 || true
echo ""
echo "Modified Files (Last 7 Days):"
git log --since="7 days ago" --name-only --pretty=format:"" | sort -u | grep -v '^$' || true
```

### 1.2 Project Structure Analysis (SAFE / NO HUGE DUMPS)

```bash
echo "=== PROJECT STRUCTURE (HIGH-LEVEL) ==="
echo ""
echo "Top-Level Structure:"
tree -L 2 -I 'node_modules|dist|.git|.DS_Store|.next|coverage' . 2>/dev/null | head -120 || true
echo ""
echo "Client Structure (prefer App Router if exists):"
if [ -d "client/app" ]; then
  echo "client/app exists (Next.js App Router)."
  tree client/app -L 2 -I 'node_modules|.next' 2>/dev/null | head -120 || true
elif [ -d "client/pages" ]; then
  echo "client/pages exists (Pages Router)."
  ls -la client/pages/ | head -120 || true
else
  echo "No client/app or client/pages found."
fi
echo ""
echo "Client Components (top-level only):"
if [ -d "client/components" ]; then
  tree client/components -L 2 -I 'node_modules' 2>/dev/null | head -120 || true
else
  echo "No client/components folder found."
fi
echo ""
echo "Documentation Files:"
if [ -d "docs" ]; then
  tree docs -L 2 2>/dev/null | head -120 || true
else
  echo "No docs/ folder found."
fi
```

### 1.3 Routes Analysis (BEST-EFFORT)

```bash
echo "=== ROUTES (BEST-EFFORT) ==="
if [ -f "client/App.tsx" ]; then
  echo "Found client/App.tsx (React Router style). Showing first 60 route lines:"
  grep -E "path=|<Route" client/App.tsx | head -60 || true
elif [ -d "client/app" ]; then
  echo "Next.js App Router detected. Listing key route folders (depth 3):"
  find client/app -maxdepth 3 -type f -name "page.tsx" -o -name "layout.tsx" 2>/dev/null | head -80 || true
else
  echo "No route source detected (client/App.tsx or client/app)."
fi
```

### 1.4 Mock API Endpoints (BEST-EFFORT)

```bash
echo "=== MOCK API ENDPOINTS (BEST-EFFORT) ==="
if [ -f "client/mocks/handlers.ts" ]; then
  grep -E "http\.(get|post|put|patch|delete)" client/mocks/handlers.ts | head -60 || true
else
  echo "No client/mocks/handlers.ts found."
fi
```

### 1.5 Current Dependencies (KEY DEPENDENCIES)

```bash
echo "=== KEY DEPENDENCIES ==="
if [ -f "package.json" ]; then
  cat package.json | grep -E '"react"|"typescript"|"next"|"vite"|"tailwindcss"|"framer-motion"|"shadcn"' | head -40 || true
else
  echo "No package.json found at repo root."
fi
```

### 1.6 AgentCore Runtime Status (MANDATORY)

Use AgentCore CLI to check all deployed agent runtimes:

```bash
echo "=== AGENTCORE RUNTIME STATUS ==="
echo ""
echo "Checking agent runtime status via AgentCore CLI..."
echo "(Reference: https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html)"
echo ""

# Check status for each SGA agent runtime
for agent in nexo_import validation observation reconciliacao reverse learning schema_evolution carrier compliance equipment_research estoque_control expedition import intake; do
  echo "--- Agent: $agent ---"
  cd server/agentcore-inventory/agents/$agent 2>/dev/null && agentcore status 2>&1 | head -20 || echo "Agent directory not found or agentcore CLI not available"
  cd - > /dev/null 2>&1 || true
done
```

**AgentCore CLI Commands Used:**
- `agentcore status` - Shows deployment status, memory config, endpoint readiness, VPC details
- `agentcore invoke` - Test agent with JSON payload (use for validation)

---

## Phase 2: Load and Analyze Existing Documentation

### 2.1 Read Current CLAUDE.md (SOURCE OF TRUTH FOR POLICIES)

```bash
echo "=== CURRENT CLAUDE.MD ==="
cat CLAUDE.md
```

### 2.2 Read Current prime.md (DO NOT BREAK THIS FILE)

```bash
echo "=== CURRENT PRIME.MD ==="
cat .claude/commands/prime.md 2>/dev/null || cat prime.md 2>/dev/null || echo "prime.md not found"
```

### 2.3 Documentation Inventory

```bash
echo "=== ALL DOCS (INDEX) ==="
if [ -d "docs" ]; then
  find docs -name "*.md" -type f | sort || true
else
  echo "No docs/ folder found."
fi
```

### 2.4 Read Architecture Docs (BEST-EFFORT)

```bash
echo "=== ARCHITECTURE DOCS (BEST-EFFORT) ==="
cat docs/architecture/FRONTEND_ARCHITECTURE.md 2>/dev/null || echo "No FRONTEND_ARCHITECTURE.md found"
```

---

## Phase 3: Search and Analyze Memory (MCP)

### 3.1 Load Full Memory Graph

```text
mcp__memory__read_graph
```

### 3.2 Search for Project-Specific Information (BEST-EFFORT QUERY)

```text
mcp__memory__search_nodes "Faiston"
```

---

## Phase 3.9: CLAUDE.md AUDIT GATE (MANDATORY)

**Goal:** Keep root `CLAUDE.md` policy-focused. Do NOT bloat it with dumps.

### Allowed in root CLAUDE.md

- Global policies (security/auth/infra/AI/model constraints/MCP rules)
- Short, stable rules that apply everywhere

### NOT allowed in root CLAUDE.md

- Long inventories (routes/components/pages/endpoints)
- Sprint logs / changelogs
- "Known issues & fixes" logs
- Large architecture dumps that change frequently

**If something is not a global policy:**

- Put it in `docs/` (ex: `docs/PROJECT_STATE.md`, `docs/KNOWN_ISSUES.md`)
- Or in module-level `CLAUDE.md` (client/server/terraform)

---

## Phase 4: UPDATE CLAUDE.md (REQUIRED)

**File:** `CLAUDE.md` (root)

### MANDATORY RULE

NEVER REMOVE OR REPLACE items marked with:

- `## DO NOT REMOVE`
- `### Important (Never Change or replace it)`
- IMMUTABLE markers/comments

### 4.1 Sections to Update (ONLY IF THEY ARE TRUE GLOBAL POLICIES)

| Section                      | What to Check/Update                         |
| ---------------------------- | -------------------------------------------- |
| Global Policies              | New non-negotiable constraints discovered    |
| Security/Infra/Auth Rules    | Only if a new universal rule was created     |
| Memory/AgentCore Constraints | Only if policy-level, stable, universal      |

### 4.2 What MUST NOT be added to CLAUDE.md

- Routes list
- Pages/components inventory
- Mock endpoints inventory
- "Known Issues & Fixes" logs
- Sprint summaries

Those belong in `docs/` and/or module `CLAUDE.md` files.

### 4.3 Execute Update (Surgical)

```bash
# Use Edit tool to update CLAUDE.md with minimal diffs.
# Do NOT rewrite the entire file.
```

---

## Phase 5: UPDATE prime.md (REQUIRED)

**File:** `.claude/commands/prime.md` (preferred) or `prime.md` (fallback)

### 5.1 What is Allowed to Update in prime.md

- Tech stack summary (only if changed)
- Where to find PRD/docs
- High-level repo map
- Minimal commands that help onboarding
- Keep it short and stable

### 5.2 What MUST NOT be added to prime.md

- Huge inventories (components/pages/hooks)
- Full changelogs
- Big "known issues" sections

### 5.3 Execute Update (Surgical)

```bash
# Use Edit tool to update prime.md with discovered changes.
# Keep the command structure intact (frontmatter + markdown).
# Do NOT rewrite the entire file.
```

---

## Phase 6: Update docs/README.md (REQUIRED)

**File:** `docs/README.md`

### 6.1 What to Update

- Add new documentation files to the index
- Update project overview if changed
- Add links to new feature docs
- Update architecture references

---

## Phase 7: Synchronize Memory (MCP)

### 7.1 Add New Observations

For each significant change discovered, add to memory:

```text
mcp__memory__add_observations
```

**Categories to update:**

- New components/pages implemented (high level only)
- New features added (decisions, not inventories)
- Architecture changes (policy-level decisions)
- Design system updates (rules, not pixel dumps)
- Route changes (only significant)
- API endpoint changes (only significant)

### 7.2 Remove Outdated Observations

If any observations are no longer accurate:

```text
mcp__memory__delete_observations
```

### 7.3 Create New Entities (if needed)

For major new features that warrant their own entity:

```text
mcp__memory__create_entities
```

---

## Phase 8: Generate Sync Report (REQUIRED)

After all updates, generate summary:

```markdown
## 🔄 Sync Report - [DATE]

### Files Updated

- [ ] CLAUDE.md - [minimal policy changes made / or NO CHANGE]
- [ ] .claude/commands/prime.md - [changes made / or NO CHANGE]
- [ ] docs/README.md - [changes made / or NO CHANGE]
- [ ] Other: [list]

### Memory Updated

- Observations added: [count]
- Observations removed: [count]
- New entities: [list if any]

### Project Current State (HIGH-LEVEL)

- Routes/pages changed: [yes/no + summary]
- Major components/features changed: [yes/no + summary]
- Infrastructure changes: [yes/no + summary]

### Changes Detected Since Last Sync

- [List key changes found]

### Recommendations

- [Any follow-up actions needed]
```

---

## Execution Rules

### MUST DO

- ✅ Read CLAUDE.md and prime.md BEFORE making changes
- ✅ Use Edit tool for precise updates (not full rewrites)
- ✅ Preserve existing structure and formatting
- ✅ Update MCP memory with significant changes
- ✅ Generate sync report at the end

### MUST NOT

- ❌ Rewrite entire files (use Edit for surgical updates)
- ❌ Remove historical info that is still accurate
- ❌ Break the structure/formatting of prime.md
- ❌ Skip the sync report

### Order of Operations

1. Analyze (Phase 1–3)
2. Audit Gate (Phase 3.9)
3. Update CLAUDE.md (Phase 4)
4. Update prime.md (Phase 5)
5. Update docs/README.md (Phase 6)
6. Sync Memory (Phase 7)
7. Generate Report (Phase 8)

---

## Quick Reference

**Command:** `/sync-project`

**Files Updated:**

| File                        | Purpose                          |
| --------------------------- | -------------------------------- |
| `CLAUDE.md`                 | Global policies (non-negotiable) |
| `.claude/commands/prime.md` | Context loading command          |
| `docs/README.md`            | Documentation hub                |
| MCP Memory                  | Knowledge graph entities         |

**When to Use:**

- ✅ After implementing new features
- ✅ After adding new pages/components
- ✅ After modifying routes or API
- ✅ Weekly maintenance
- ✅ Before major development sessions
- ✅ After merging branches

---

## References (Best Practices)

- Slash commands: <https://code.claude.com/docs/en/slash-commands>
- Claude Code best practices: <https://www.anthropic.com/engineering/claude-code-best-practices>
