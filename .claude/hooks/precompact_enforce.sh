#!/usr/bin/env bash
# precompact_enforce.sh - PreCompact hook that enforces /sync-project before compaction
# Blocks compaction if /sync-project was not run recently (default: 30 min)
# If allowed, creates prime_required.flag for post-compact prime injection
set -euo pipefail

STATE_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks_state"
MARKER_FILE="$STATE_DIR/last_sync_project.utc"
FLAG_FILE="$STATE_DIR/prime_required.flag"
FRESHNESS_MINUTES=${COMPACT_SYNC_FRESHNESS_MINUTES:-30}

# Check if marker exists
if [[ ! -f "$MARKER_FILE" ]]; then
  cat <<EOF
{
  "continue": false,
  "stopReason": "COMPACTION BLOCKED: /sync-project has not been run. Run /sync-project first, then run /compact again."
}
EOF
  exit 0
fi

# Check freshness using Python for cross-platform (macOS/Linux) compatibility
MARKER_AGE_MINUTES=$(python3 -c "
import os, time
mtime = os.path.getmtime('$MARKER_FILE')
age_seconds = time.time() - mtime
print(int(age_seconds / 60))
" 2>/dev/null || echo "999")

if [[ "$MARKER_AGE_MINUTES" -gt "$FRESHNESS_MINUTES" ]]; then
  cat <<EOF
{
  "continue": false,
  "stopReason": "COMPACTION BLOCKED: /sync-project was run ${MARKER_AGE_MINUTES} minutes ago (max: ${FRESHNESS_MINUTES}). Run /sync-project again, then /compact."
}
EOF
  exit 0
fi

# Allow compaction and set prime_required flag
mkdir -p "$STATE_DIR"
touch "$FLAG_FILE"

# Exit cleanly - no JSON output means "continue: true" implicitly
exit 0
