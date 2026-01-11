# Claude Code Hooks

This document describes the custom Claude Code hooks configured for this repository.

## Purpose: Continuous Context

These hooks implement **CONTINUOUS CONTEXT** so Claude Code never drifts and always has:
1. **IMMUTABLE rules** injected before every prompt
2. **CONTEXT_SNAPSHOT.md** injected before every prompt
3. **CONTEXT_SNAPSHOT.md** updated after every response
4. **WORKLOG.md** appended after every response (audit trail)

---

## Enabled Hooks

### 1. UserPromptSubmit: Context Injection

**Script:** `.claude/hooks/inject_context.sh`

**Purpose:** Injects IMMUTABLE rules AND current project context before every prompt.

**What it injects:**
1. **IMMUTABLE block** from `CLAUDE.md`
   - Extracted dynamically using markers (not hardcoded line numbers)
   - Start marker: `IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE`
   - End marker: `END OF IMMUTABLE BLOCK`
   - Fallback: first 200 lines if markers not found

2. **CONTEXT_SNAPSHOT.md**
   - Current project state (goal, plan, last turn summary, constraints)
   - If file doesn't exist yet, injects placeholder message

**Output format:**
```
--- INJECTED CLAUDE.MD RULES (IMMUTABLE BLOCK) ---
[IMMUTABLE block content]
--- END INJECTED RULES ---

--- CURRENT PROJECT CONTEXT SNAPSHOT ---
[CONTEXT_SNAPSHOT.md content or placeholder]
--- END CONTEXT SNAPSHOT ---
```

---

### 2. Stop: Post-Turn Update

**Script:** `.claude/hooks/post_turn_update.py`

**Purpose:** Updates context files after each Claude Code response.

**What it updates:**

#### A. `docs/CONTEXT_SNAPSHOT.md` (OVERWRITE)

Fixed format (~30 lines):
```markdown
# CONTEXT SNAPSHOT (AUTO)
Updated: <UTC timestamp>

## Current Goal
- <inferred from last user message>

## Current Plan (Next 3 Steps)
1. <step>
2. <step>
3. <step>

## Last Turn Summary
- User: <max 240 chars>
- Assistant: <max 240 chars>

## Active Constraints (from CLAUDE.md)
- <6 key constraints>

## Risks / Blockers
- <if any>
```

#### B. `docs/WORKLOG.md` (APPEND)

Audit trail format:
```markdown
## Turn Log — <UTC timestamp>

**User:** <max 1200 chars>

**Assistant:** <max 1200 chars>

---
```

---

## HARDCORE Blocking Mode

The Stop hook implements **blocking on failure**. If any update fails, the hook returns:

```json
{"decision": "block", "reason": "Post-turn context update failed: <reason>. Fix hooks or set CLAUDE_HOOKS_ALLOW_FAIL=true temporarily."}
```

This ensures context updates cannot be silently skipped.

### Escape Hatch

To temporarily disable blocking (for debugging or emergencies):

```bash
export CLAUDE_HOOKS_ALLOW_FAIL=true
```

With this set, the hook logs errors to stderr but does **NOT** block.

---

## Configuration Location

Hooks are configured in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/inject_context.sh\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/post_turn_update.py\""
          }
        ]
      }
    ]
  }
}
```

---

## Enable/Disable Hooks

### Disable All Hooks Temporarily

Add to settings:
```json
{
  "disableAllHooks": true
}
```

### Disable Individual Hook

Remove or comment out the specific hook entry in `settings.local.json`.

---

## Testing Hooks

### Test 1: Context Injection

```bash
cd /Users/fabio.santos/LPD\ Repos/lpd-faiston-allinone
bash .claude/hooks/inject_context.sh | head -80
```

Expected output:
```
--- INJECTED CLAUDE.MD RULES (IMMUTABLE BLOCK) ---
<!-- ===================================================== -->
<!-- 🔒 IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE 🔒       -->
...
--- END INJECTED RULES ---

--- CURRENT PROJECT CONTEXT SNAPSHOT ---
# CONTEXT SNAPSHOT (AUTO)
...
--- END CONTEXT SNAPSHOT ---
```

### Test 2: Stop Hook (Success)

```bash
# Create mock transcript
echo '{"role":"user","content":"Test user message for hooks verification"}' > /tmp/claude_transcript.jsonl
echo '{"role":"assistant","content":"Test assistant response - hooks are working correctly"}' >> /tmp/claude_transcript.jsonl

# Run hook
cd /Users/fabio.santos/LPD\ Repos/lpd-faiston-allinone
echo '{"transcript_path":"/tmp/claude_transcript.jsonl","stop_hook_active":false}' | python3 .claude/hooks/post_turn_update.py

# Verify CONTEXT_SNAPSHOT.md
cat docs/CONTEXT_SNAPSHOT.md

# Verify WORKLOG.md
tail -20 docs/WORKLOG.md
```

### Test 3: Stop Hook (Blocking on Failure)

```bash
echo '{"transcript_path":"/tmp/does_not_exist.jsonl","stop_hook_active":false}' | python3 .claude/hooks/post_turn_update.py
```

Expected output:
```json
{"decision":"block","reason":"Post-turn context update failed: Transcript file not found: /tmp/does_not_exist.jsonl. Fix hooks or set CLAUDE_HOOKS_ALLOW_FAIL=true temporarily."}
```

### Test 4: Escape Hatch

```bash
CLAUDE_HOOKS_ALLOW_FAIL=true echo '{"transcript_path":"/tmp/does_not_exist.jsonl","stop_hook_active":false}' | python3 .claude/hooks/post_turn_update.py
```

Expected: No blocking JSON (error logged to stderr only).

---

## Safety Features

1. **No infinite loops:** The `stop_hook_active` flag prevents recursion
2. **No secrets:** Scripts never read or print sensitive files (.env, credentials)
3. **Fail-safe injection:** Context injection failures don't block (just warn)
4. **Python stdlib only:** No external dependencies
5. **POSIX bash:** Uses `set -euo pipefail` for safe execution

---

## Troubleshooting

### Hook not running?

1. Check `disableAllHooks` is not set to `true`
2. Verify scripts are executable: `chmod +x .claude/hooks/*.sh .claude/hooks/*.py`
3. Validate `settings.local.json` syntax

### CONTEXT_SNAPSHOT.md not updating?

1. Check `docs/` directory exists
2. Verify file permissions
3. Check stderr for error messages: `python3 .claude/hooks/post_turn_update.py 2>&1`

### Getting blocked unexpectedly?

Set escape hatch and investigate:
```bash
export CLAUDE_HOOKS_ALLOW_FAIL=true
# Then run Claude Code and check stderr for actual error
```

### IMMUTABLE block not extracting correctly?

Test extraction directly:
```bash
# Check markers exist
grep -n "IMMUTABLE BLOCK" CLAUDE.md

# Test extraction
sed -n '/IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE/,/END OF IMMUTABLE BLOCK/p' CLAUDE.md | head -50
```

---

## Files

| File | Purpose |
|------|---------|
| `.claude/hooks/inject_context.sh` | UserPromptSubmit hook (context injection) |
| `.claude/hooks/post_turn_update.py` | Stop hook (context + worklog update) |
| `docs/CONTEXT_SNAPSHOT.md` | Current project state (auto-updated) |
| `docs/WORKLOG.md` | Audit trail of all turns (append-only) |
| `.claude/settings.local.json` | Hook configuration (local, not committed) |

---

## CLAUDE.md Reference

These hooks implement the mandatory policy from CLAUDE.md (lines 68-72):

> **HOOKS ENFORCEMENT (MANDATORY):** Claude Code Hooks MUST be enabled to enforce continuous rule priming and continuous session context:
> - `UserPromptSubmit` MUST inject essential rules from `CLAUDE.md` (prefer IMMUTABLE block) AND inject the current living context from `docs/CONTEXT_SNAPSHOT.md`.
> - `Stop` MUST update `docs/CONTEXT_SNAPSHOT.md` after every response (post-turn context refresh) AND append to `docs/WORKLOG.md` (audit trail).
> - If the post-turn update fails, the Stop hook MUST **BLOCK** completion (unless `CLAUDE_HOOKS_ALLOW_FAIL=true` is explicitly set as a temporary override).
