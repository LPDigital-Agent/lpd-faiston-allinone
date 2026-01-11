# Compaction Workflow Enforcement

This document describes the automated workflow that ensures context integrity during Claude Code compaction operations.

---

## Overview

Compaction (`/compact` or automatic) compresses the conversation context to free up tokens. Without proper safeguards, this can cause:

1. **Context drift** — Loss of critical project rules and constraints
2. **Memory loss** — Project state not persisted before compaction
3. **Rule amnesia** — CLAUDE.md immutable block not reloaded after compaction

This implementation enforces a mandatory workflow:

```
/sync-project → /compact → auto-/prime
```

---

## How It Works

### Phase 1: Pre-Compact Enforcement

**Hook:** `PreCompact` → `.claude/hooks/precompact_enforce.sh`

**Behavior:**
1. Checks if `/sync-project` was run recently (marker file exists and is fresh)
2. **If NOT fresh (>30 minutes):** Blocks compaction with message
3. **If fresh:** Allows compaction and sets `prime_required.flag`

**Marker file:** `.claude/hooks_state/last_sync_project.utc`
- Format: `2026-01-11T17:30:00Z sha=abc1234`
- Created by: `/sync-project` command via Stop hook

### Phase 2: Sync Marker Writing

**Trigger:** `/sync-project` command completion
**Hook:** Command-scoped Stop hook in `sync-project.md` frontmatter
**Script:** `.claude/hooks/mark_sync_done.sh`

**Behavior:**
- Writes UTC timestamp + git SHA to marker file
- Ensures compaction is allowed for next 30 minutes

### Phase 3: Post-Compact Prime Injection

**Hook:** `UserPromptSubmit` → `.claude/hooks/postcompact_prime_inject.sh`

**Behavior:**
1. Checks if `.claude/hooks_state/prime_required.flag` exists
2. **If exists:** Injects prime context, then removes flag
3. **If not exists:** Does nothing (lets normal `inject_context.sh` run)

**Injected context includes:**
- CLAUDE.md IMMUTABLE block
- Current git state (branch, status, recent commits)
- Project structure overview
- AgentCore runtimes summary

---

## File Structure

```
.claude/
├── hooks/
│   ├── mark_sync_done.sh         # Writes sync timestamp marker
│   ├── precompact_enforce.sh     # PreCompact gate (blocks if no sync)
│   ├── postcompact_prime_inject.sh # Injects prime after compaction
│   ├── inject_context.sh         # Normal context injection (unchanged)
│   └── post_turn_update.py       # Stop hook (unchanged)
├── hooks_state/
│   ├── last_sync_project.utc     # Sync timestamp marker
│   └── prime_required.flag       # Set by PreCompact, cleared by prime inject
├── commands/
│   └── sync-project.md           # Has Stop hook to call mark_sync_done.sh
└── settings.local.json           # Hook configuration
```

---

## Configuration

### settings.local.json (hooks section)

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/precompact_enforce.sh\""
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/postcompact_prime_inject.sh\""
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/inject_context.sh\""
          }
        ]
      }
    ]
  }
}
```

### sync-project.md frontmatter

```yaml
---
name: sync-project
hooks:
  Stop:
    - type: command
      command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/mark_sync_done.sh"
---
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPACT_SYNC_FRESHNESS_MINUTES` | 30 | How many minutes a sync marker is considered fresh |
| `CLAUDE_PROJECT_DIR` | `.` | Project root (set automatically by Claude Code) |

---

## Emergency Overrides

### Skip PreCompact Check

If you need to force compaction without `/sync-project`:

```bash
# Manually create a fresh marker
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") sha=manual" > .claude/hooks_state/last_sync_project.utc
```

### Skip Post-Compact Prime

If prime injection is causing issues:

```bash
# Remove the flag manually
rm -f .claude/hooks_state/prime_required.flag
```

---

## Testing

### Test 1: Marker Writing

```bash
# Run /sync-project, then verify
cat .claude/hooks_state/last_sync_project.utc
# Expected: 2026-01-11T17:30:00Z sha=abc1234
```

### Test 2: PreCompact Block

```bash
# Delete marker and test hook directly
rm -f .claude/hooks_state/last_sync_project.utc
echo '{}' | bash .claude/hooks/precompact_enforce.sh
# Expected: {"continue": false, "stopReason": "..."}
```

### Test 3: PreCompact Allow

```bash
# Create fresh marker and test
bash .claude/hooks/mark_sync_done.sh
echo '{}' | bash .claude/hooks/precompact_enforce.sh
# Expected: No output (exit 0), flag created
ls .claude/hooks_state/prime_required.flag
```

### Test 4: Post-Compact Prime

```bash
# Simulate post-compact state
touch .claude/hooks_state/prime_required.flag
bash .claude/hooks/postcompact_prime_inject.sh | head -50
# Expected: Prime context output, flag removed
```

---

## Troubleshooting

### Compaction Blocked Unexpectedly

**Symptom:** `/compact` shows "Run /sync-project first"

**Solution:**
1. Run `/sync-project` to create fresh marker
2. Or manually create marker (see Emergency Overrides)

### Prime Not Injected After Compact

**Symptom:** Context seems incomplete after compaction

**Check:**
1. Verify `prime_required.flag` was created during compact
2. Check `postcompact_prime_inject.sh` is in UserPromptSubmit hooks
3. Test hook directly: `bash .claude/hooks/postcompact_prime_inject.sh`

### Marker File Not Created

**Symptom:** `/sync-project` runs but marker doesn't appear

**Check:**
1. Verify `sync-project.md` has Stop hook in frontmatter
2. Verify `.claude/hooks_state/` directory exists
3. Test script directly: `bash .claude/hooks/mark_sync_done.sh`

---

## Related Documentation

- `docs/Claude Code/HOOKS.md` — Full hooks system documentation
- `.claude/commands/sync-project.md` — Sync command details
- `.claude/commands/prime.md` — Prime command details
- `CLAUDE.md` — Global project rules (IMMUTABLE block)
