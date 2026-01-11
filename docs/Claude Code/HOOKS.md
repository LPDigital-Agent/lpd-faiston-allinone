# Claude Code Hooks

This document describes the custom Claude Code hooks configured for this repository.

## Enabled Hooks

### 1. UserPromptSubmit: Context Injection

**Script:** `.claude/hooks/inject_claude_rules.sh`

**Purpose:** Automatically injects the IMMUTABLE block from `CLAUDE.md` into every prompt's context, ensuring critical rules are always "fresh" in Claude's memory.

**What it does:**
- Extracts lines 13-488 from `CLAUDE.md` (the IMMUTABLE block)
- Falls back to first 160 lines if extraction fails
- Outputs extracted rules to stdout (Claude Code adds to context)

### 2. Stop: Work Log Memory

**Script:** `.claude/hooks/post_turn_memory.py`

**Purpose:** Maintains a running, human-readable record of work and decisions in `docs/WORKLOG.md`.

**What it does:**
- Reads transcript from Claude Code's payload
- Extracts latest user message and assistant response
- Appends timestamped entry to `docs/WORKLOG.md`
- **HARDCORE MODE:** Blocks if update fails (see below)

## HARDCORE Blocking Mode

The Stop hook implements **blocking on failure**. If the WORKLOG update fails for any reason, the hook returns:

```json
{"decision": "block", "reason": "WORKLOG update failed: <reason>. Fix hooks or disable block mode."}
```

This ensures failures cannot be silently ignored.

### Escape Hatch

To temporarily disable blocking (e.g., for debugging):

```bash
export CLAUDE_HOOKS_ALLOW_FAIL=true
```

With this set, the hook will log errors to stderr but NOT block.

## Configuration Location

Hooks are configured in `.claude/settings.local.json` (not committed by default).

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/inject_claude_rules.sh\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/post_turn_memory.py\""
          }
        ]
      }
    ]
  }
}
```

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

## Promote to Shared Settings

Once verified, promote hooks to the shared settings file:

1. Copy the hooks section from `.claude/settings.local.json`
2. Paste into `.claude/settings.json`
3. Commit `.claude/settings.json`

**Note:** `.claude/settings.local.json` is gitignored and takes precedence over `.claude/settings.json`.

## Testing Hooks

### Test Context Injection Hook

```bash
bash .claude/hooks/inject_claude_rules.sh | head -40
```

Should output:
```
--- INJECTED CLAUDE.MD RULES (IMMUTABLE BLOCK) ---
<!-- ===================================================== -->
<!-- IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE       -->
...
```

### Test Work Log Hook (Success)

```bash
# Create mock transcript
echo '{"role":"user","content":"Test user message"}' > /tmp/claude_transcript.jsonl
echo '{"role":"assistant","content":"Test assistant response"}' >> /tmp/claude_transcript.jsonl

# Run hook
echo '{"transcript_path":"/tmp/claude_transcript.jsonl","stop_hook_active":false}' | python3 .claude/hooks/post_turn_memory.py

# Check result
cat docs/WORKLOG.md
```

### Test Work Log Hook (Failure/Blocking)

```bash
# Test with non-existent file
echo '{"transcript_path":"/tmp/does_not_exist.jsonl","stop_hook_active":false}' | python3 .claude/hooks/post_turn_memory.py
```

Should output:
```json
{"decision":"block","reason":"WORKLOG update failed: Transcript file not found: /tmp/does_not_exist.jsonl. Fix hooks or disable block mode."}
```

### Test Escape Hatch

```bash
CLAUDE_HOOKS_ALLOW_FAIL=true \
echo '{"transcript_path":"/tmp/does_not_exist.jsonl","stop_hook_active":false}' | python3 .claude/hooks/post_turn_memory.py
```

Should NOT output blocking JSON (logs to stderr instead).

## Safety Notes

1. **No infinite loops:** The `stop_hook_active` flag prevents recursion
2. **No secrets:** Scripts do not read or print sensitive files
3. **Fail-safe:** Context injection failures don't block (just warn)
4. **Stdlib only:** Python hook uses no external dependencies

## Troubleshooting

### Hook not running?

1. Check `disableAllHooks` is not set to `true`
2. Verify script is executable: `chmod +x .claude/hooks/*.sh`
3. Check settings.local.json syntax with a JSON validator

### WORKLOG not updating?

1. Ensure `docs/` directory exists
2. Check for file permission issues
3. Verify transcript path is valid
4. Check stderr for error messages

### Getting blocked unexpectedly?

Set escape hatch:
```bash
export CLAUDE_HOOKS_ALLOW_FAIL=true
```

Then investigate the root cause in hook output.
