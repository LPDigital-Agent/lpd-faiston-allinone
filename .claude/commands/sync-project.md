---
name: sync-project
description: Sync and update all project documentation, memory, and reference files to reflect current project state
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoRead, TodoWrite, mcp__memory__read_graph, mcp__memory__create_entities, mcp__memory__add_observations, mcp__memory__create_relations, mcp__memory__search_nodes, mcp__memory__delete_observations
---

# Sync Project - Complete Project State Update

This command performs a comprehensive synchronization of all project documentation, memory entities, and reference files to ensure they accurately reflect the current state of the project.

---

## Phase 1: Analyze Current Project State

### 1.1 Git Repository State

```bash
echo "=== GIT STATE ==="
echo "Branch: $(git branch --show-current)"
echo ""
echo "Uncommitted Changes:"
git status --short
echo ""
echo "Recent Commits (Last 10):"
git log --oneline -10
echo ""
echo "Modified Files (Last 7 Days):"
git log --since="7 days ago" --name-only --pretty=format:"" | sort -u | grep -v '^$'
```

### 1.2 Project Structure Analysis

```bash
echo "=== PROJECT STRUCTURE ==="
echo ""
echo "Top-Level Structure:"
tree -L 2 -I 'node_modules|dist|.git|.DS_Store' . 2>/dev/null
echo ""
echo "Client Pages:"
ls -la client/pages/
echo ""
echo "Client Components:"
tree client/components -L 2 -I 'node_modules' 2>/dev/null
echo ""
echo "Documentation Files:"
tree docs -L 2 2>/dev/null
```

### 1.3 Routes Analysis

```bash
echo "=== ROUTES (App.tsx) ==="
grep -E "path=|<Route" client/App.tsx | head -30
```

### 1.4 Mock API Endpoints

```bash
echo "=== MOCK API ENDPOINTS ==="
grep -E "http\.(get|post|put|patch|delete)" client/mocks/handlers.ts | head -30
```

### 1.5 Current Dependencies

```bash
echo "=== KEY DEPENDENCIES ==="
cat package.json | grep -E '"react"|"typescript"|"vite"|"tailwindcss"|"framer-motion"' | head -20
```

---

## Phase 2: Load and Analyze Existing Documentation

### 2.1 Read Current CLAUDE.md

```bash
echo "=== CURRENT CLAUDE.MD ==="
cat CLAUDE.md
```

### 2.2 Read Current prime.md

```bash
echo "=== CURRENT PRIME.MD ==="
cat .claude/commands/prime.md
```

### 2.3 Documentation Inventory

```bash
echo "=== ALL DOCS ==="
find docs -name "*.md" -type f | sort
```

### 2.4 Read Architecture Docs

```bash
echo "=== ARCHITECTURE DOCS ==="
cat docs/architecture/FRONTEND_ARCHITECTURE.md 2>/dev/null || echo "No architecture doc found"
```

---

## Phase 3: Search and Analyze Memory (MCP)

### 3.1 Load Full Memory Graph

```mcp
mcp__memory__read_graph
```

### 3.2 Search for Project-Specific Information

```mcp
mcp__memory__search_nodes "Hive Academy"
```

---

## Phase 4: UPDATE CLAUDE.md (REQUIRED)

**File**: `CLAUDE.md` (root)

Based on Phase 1 analysis, UPDATE the following sections in CLAUDE.md:

### 4.1 Sections to Update

| Section | What to Check/Update |
|---------|---------------------|
| **Directory Structure** | New folders/components in `client/` |
| **Current Routes** | New routes in `App.tsx` |
| **Mock API** | New endpoints in `handlers.ts` |
| **Key Features** | New features implemented |
| **Design System** | New colors, typography, patterns |
| **Known Issues & Fixes** | New bugs discovered and fixed |

### 4.2 Update Checklist

- [ ] Add any NEW pages to Routes section
- [ ] Add any NEW components to Directory Structure
- [ ] Add any NEW mock endpoints to Mock API section
- [ ] Add any NEW features to Key Features section
- [ ] Update Design System if colors/typography changed
- [ ] Add any NEW known issues & fixes
- [ ] Update dev port if changed

### 4.3 Execute Update

```bash
# Use Edit tool to update CLAUDE.md with discovered changes
# Example: Add new route, component, or feature section
```

**IMPORTANT**: Use the `Edit` tool to make precise updates. Do NOT rewrite the entire file.

---

## Phase 5: UPDATE prime.md (REQUIRED)

**File**: `.claude/commands/prime.md`

### 5.1 Sections to Update in prime.md

| Section | What to Check/Update |
|---------|---------------------|
| **Tech Stack Summary** | Version changes in package.json |
| **Directory Structure** | New folders added |
| **Application Routes** | New routes added |
| **Mock Endpoints** | New API endpoints |
| **Project Identity** | Any major changes |

### 5.2 Update Checklist for prime.md

- [ ] Update Tech Stack table if versions changed
- [ ] Add new directories to Directory Structure
- [ ] Update Application Routes with new pages
- [ ] Update Mock endpoints table
- [ ] Ensure Quick Reference commands are current

### 5.3 Execute Update

```bash
# Use Edit tool to update .claude/commands/prime.md
# Keep the command structure intact, only update content
```

**IMPORTANT**: prime.md is a Claude Code command - maintain its structure with `---` frontmatter and markdown sections.

---

## Phase 6: Update docs/README.md

**File**: `docs/README.md`

### 6.1 What to Update

- [ ] Add new documentation files to the index
- [ ] Update project overview if changed
- [ ] Add links to new feature docs
- [ ] Update architecture references

---

## Phase 7: Synchronize Memory (MCP)

### 7.1 Add New Observations

For each significant change discovered, add to memory:

```mcp
mcp__memory__add_observations
```

**Categories to update**:
- New components/pages implemented
- New features added
- Architecture changes
- Design system updates
- Route changes
- API endpoint changes

### 7.2 Remove Outdated Observations

If any observations are no longer accurate:

```mcp
mcp__memory__delete_observations
```

### 7.3 Create New Entities (if needed)

For major new features that warrant their own entity:

```mcp
mcp__memory__create_entities
```

---

## Phase 8: Generate Sync Report

After all updates, generate summary:

```markdown
## 🔄 Sync Report - [DATE]

### Files Updated
- [ ] CLAUDE.md - [changes made]
- [ ] .claude/commands/prime.md - [changes made]
- [ ] docs/README.md - [changes made]
- [ ] Other: [list]

### Memory Updated
- Observations added: [count]
- Observations removed: [count]
- New entities: [list if any]

### Project Current State
- Pages: [count]
- Components: [count] 
- Routes: [count]
- Mock endpoints: [count]

### Changes Detected Since Last Sync
- [List key changes found]

### Recommendations
- [Any follow-up actions needed]
```

---

## Execution Rules

### MUST DO:
1. ✅ Read CLAUDE.md and prime.md BEFORE making changes
2. ✅ Use `Edit` tool for precise updates (not full rewrites)
3. ✅ Preserve existing structure and formatting
4. ✅ Update Memory with significant changes
5. ✅ Generate sync report at the end

### MUST NOT:
1. ❌ Rewrite entire files (use Edit for surgical updates)
2. ❌ Remove historical information that's still accurate
3. ❌ Change file structure/formatting of prime.md command
4. ❌ Skip the sync report

### Order of Operations:
1. Analyze (Phase 1-3)
2. Update CLAUDE.md (Phase 4)
3. Update prime.md (Phase 5)
4. Update docs/README.md (Phase 6)
5. Sync Memory (Phase 7)
6. Generate Report (Phase 8)

---

## Quick Reference

**Command**: `/sync-project`

**Files Updated**:
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project instructions & reference |
| `.claude/commands/prime.md` | Context loading command |
| `docs/README.md` | Documentation hub |
| MCP Memory | Knowledge graph entities |

**When to Use**:
- ✅ After implementing new features
- ✅ After adding new pages/components
- ✅ After modifying routes or API
- ✅ Weekly maintenance
- ✅ Before major development sessions
- ✅ After merging branches

**Duration**: ~5-10 minutes

---

## Post-Sync

After running sync:
1. Review changes with `git diff`
2. Run `/commit` to save documentation updates
3. Verify dev server still works: `pnpm dev`
