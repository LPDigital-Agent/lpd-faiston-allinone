---
name: update-memory
description: Update CLAUDE.md with lessons learned and rules from the current coding session. Surgically adds NEW items only - never duplicates existing rules.
allowed-tools: ["Read", "Edit", "Grep", "Glob", "Bash"]
---

# /update-memory Command

Update `CLAUDE.md` with lessons learned, patterns discovered, and rules applied during this coding session.

## CRITICAL RULES

1. **NO DUPLICATES** - If a rule/pattern/item already exists in CLAUDE.md, leave it as-is
2. **SURGICAL EDITS ONLY** - Use Edit tool, never rewrite entire file
3. **PRESERVE IMMUTABLE BLOCKS** - NEVER modify sections marked with `🔒 IMMUTABLE`
4. **ADD, DON'T REPLACE** - Only append new items to existing sections

---

## PHASE 1: Analyze Session Changes

First, understand what was done in this session:

```bash
# Recent commits (this session)
git log --oneline -10

# Files changed recently
git diff --name-only HEAD~3..HEAD 2>/dev/null || git diff --name-only HEAD~1..HEAD

# Current staged/unstaged changes
git status --short
```

**Extract from session:**
- New patterns implemented
- Architecture decisions made
- Rules that guided implementation
- Problems solved and how
- New file locations/references

---

## PHASE 2: Read Current CLAUDE.md

Read the current state to understand existing content:

```
Read /Users/fabio.santos/LPD Repos/lpd-faiston-allinone/CLAUDE.md
```

**Identify existing sections:**
- Immutable blocks (🔒) - DO NOT TOUCH
- Architectural patterns list
- Key file references
- Policies and rules
- Module-specific guidance

---

## PHASE 3: Check for Duplicates

Before adding anything, verify it doesn't already exist:

**Checklist for each potential addition:**
- [ ] Search CLAUDE.md for similar keywords
- [ ] Check if the concept is covered (even with different wording)
- [ ] Verify the pattern/rule isn't implied by existing rules

**If item exists:** SKIP IT - leave as-is
**If item is NEW:** Mark for addition

---

## PHASE 4: Categorize New Items

Organize new items by where they belong in CLAUDE.md:

| Category | Section in CLAUDE.md | Example |
|----------|---------------------|---------|
| Architectural Pattern | `SGA ARCHITECTURAL PATTERNS` | "Schema Evolution Pattern" |
| File Reference | `KEY FILE REFERENCES` | "DB Migrations: schema/*.sql" |
| Policy/Rule | Appropriate policy section | "Always use advisory locks" |
| Module Guidance | Subdirectory CLAUDE.md | Component-specific rules |

**Note:** If an item is too specific for root CLAUDE.md, it should go in a subdirectory `CLAUDE.md` file instead.

---

## PHASE 5: Surgical Updates

Use Edit tool to add ONLY new items:

**Pattern for adding to a numbered list:**
```
Edit CLAUDE.md
old_string: |
  6. **Existing Pattern:**
     - Description here

new_string: |
  6. **Existing Pattern:**
     - Description here

  7. **New Pattern Name:**
     - Key point 1
     - Key point 2
     - Reference: `path/to/relevant/file.py`
```

**Pattern for adding to KEY FILE REFERENCES:**
```
Edit CLAUDE.md
old_string: |
  - **Existing Reference**: `path/here`

new_string: |
  - **Existing Reference**: `path/here`
  - **New Reference**: `new/path/here`
```

---

## PHASE 6: Validation

After edits, verify:

1. **No broken formatting:**
   ```bash
   # Quick visual check
   head -100 CLAUDE.md
   ```

2. **Immutable blocks intact:**
   - Grep for `🔒 IMMUTABLE` markers
   - Ensure they weren't modified

3. **No accidental duplicates:**
   - Re-read updated sections
   - Verify each new item is unique

---

## PHASE 7: Generate Report

Provide a summary to the user:

```markdown
## Memory Update Summary

### Items Added:
- [ ] Pattern: "Name" → Added to SGA ARCHITECTURAL PATTERNS
- [ ] Reference: "path/file" → Added to KEY FILE REFERENCES

### Items Skipped (already exist):
- [ ] "Rule X" - Already covered in section Y
- [ ] "Pattern Z" - Exists as pattern #N

### Recommendations:
- Consider adding detailed docs to `docs/architecture/`
- Module-specific rules should go in `server/module/CLAUDE.md`
```

---

## WHAT TO ADD (Examples)

**Good additions:**
- New architectural patterns discovered
- New file paths that are frequently referenced
- Rules that prevented bugs or guided decisions
- Integration patterns between components

**NOT to add:**
- One-time fixes (too specific)
- Temporary workarounds
- Items already covered by existing rules
- Verbose explanations (keep concise)

---

## WHAT NEVER TO MODIFY

These sections are **IMMUTABLE** and must NEVER be changed:

1. `🔒 [IMMUTABLE][DO-NOT-REMOVE]` header block
2. `🔒 END OF IMMUTABLE BLOCK` footer
3. Anything between these markers
4. Core policies (Authentication, AWS Configuration, Infrastructure)

If you believe an immutable section needs updating, **STOP AND ASK** the user for explicit approval.

---

## SUBDIRECTORY CLAUDE.md FILES

If lessons learned are module-specific, update the appropriate subdirectory file:

- `server/agentcore-inventory/CLAUDE.md` - Inventory agent rules
- `server/agentcore-nexo/CLAUDE.md` - NEXO agent rules
- `terraform/CLAUDE.md` - Infrastructure rules
- `web/CLAUDE.md` - Frontend rules

Use the same surgical Edit approach for these files.
