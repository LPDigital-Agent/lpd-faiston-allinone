#!/usr/bin/env bash
# postcompact_prime_inject.sh - UserPromptSubmit hook that injects /prime context after compaction
# Triggers when: prime_required.flag exists (set by precompact_enforce.sh)
# Action: Inject essential context, then remove flag
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
STATE_DIR="$PROJECT_DIR/.claude/hooks_state"
FLAG_FILE="$STATE_DIR/prime_required.flag"

# If no flag, exit silently (let normal inject_context.sh handle context)
if [[ ! -f "$FLAG_FILE" ]]; then
  exit 0
fi

# Flag exists → inject prime context
cat <<'HEADER'
--- POST-COMPACT PRIME INJECTION (AUTO) ---
Context was compacted. Reloading essential project context...

HEADER

# Inject CLAUDE.md IMMUTABLE block (same extraction logic as inject_context.sh)
CLAUDE_FILE="$PROJECT_DIR/CLAUDE.md"
if [[ -f "$CLAUDE_FILE" ]]; then
  echo "--- INJECTED CLAUDE.MD RULES (IMMUTABLE BLOCK) ---"
  # Extract between IMMUTABLE markers, fallback to first 200 lines if markers not found
  IMMUTABLE_CONTENT=$(sed -n '/IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE/,/END OF IMMUTABLE BLOCK/p' "$CLAUDE_FILE" 2>/dev/null)
  if [[ -n "$IMMUTABLE_CONTENT" ]]; then
    echo "$IMMUTABLE_CONTENT"
  else
    head -200 "$CLAUDE_FILE"
  fi
fi

# Inject current git state
echo ""
echo "--- CURRENT GIT STATE ---"
cd "$PROJECT_DIR" 2>/dev/null || true
echo "Branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"
git status --short 2>/dev/null | head -20 || echo "(no git status)"
echo ""
echo "Recent commits:"
git log --oneline -5 2>/dev/null || echo "(no commits)"

# Inject minimal project structure
echo ""
echo "--- PROJECT STRUCTURE ---"
ls -la "$PROJECT_DIR" 2>/dev/null | head -25 || echo "(could not list)"

# Inject AgentCore runtimes reminder
cat <<'RUNTIMES'

--- AGENTCORE RUNTIMES ---
| Runtime                | Agents | Purpose                   |
| ---------------------- | ------ | ------------------------- |
| agentcore-inventory    | 14     | SGA - Inventory Management |
| agentcore-academy      | 6      | Learning Platform          |
| agentcore-portal       | 2      | NEXO Orchestrator          |
RUNTIMES

# Remove flag after successful injection
rm -f "$FLAG_FILE"

cat <<'FOOTER'

--- END POST-COMPACT PRIME ---
Prime context loaded. Ready for your next task.
FOOTER
