#!/usr/bin/env bash
# inject_context.sh - Injects IMMUTABLE rules + CONTEXT_SNAPSHOT into Claude Code context
# Hook: UserPromptSubmit
# Purpose: Continuous context injection before every prompt
#
# WHAT IT INJECTS:
#   1. IMMUTABLE block from CLAUDE.md (dynamically extracted via markers)
#   2. Current CONTEXT_SNAPSHOT.md (or placeholder if missing)

set -euo pipefail

# Use project directory from Claude Code env var, fallback to script location
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
CLAUDE_MD="${PROJECT_DIR}/CLAUDE.md"
CONTEXT_SNAPSHOT="${PROJECT_DIR}/docs/CONTEXT_SNAPSHOT.md"

# --- FUNCTION: Extract IMMUTABLE block using markers ---
extract_immutable() {
    local start_marker="IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE"
    local end_marker="END OF IMMUTABLE BLOCK"

    # Use sed to extract between markers (inclusive of marker lines)
    # -n: suppress auto-print, /start/,/end/p: print from start to end pattern
    local extracted
    extracted=$(sed -n "/${start_marker}/,/${end_marker}/p" "$CLAUDE_MD" 2>/dev/null || true)

    # Validate extraction contains IMMUTABLE keyword
    if [[ -n "$extracted" ]] && echo "$extracted" | grep -q "IMMUTABLE"; then
        echo "$extracted"
    else
        # Fallback: first 200 lines (better coverage than 160)
        echo "[WARN] Could not extract IMMUTABLE block via markers, using fallback" >&2
        head -200 "$CLAUDE_MD"
    fi
}

# --- FUNCTION: Inject CONTEXT_SNAPSHOT or placeholder ---
inject_snapshot() {
    if [[ -f "$CONTEXT_SNAPSHOT" ]]; then
        cat "$CONTEXT_SNAPSHOT"
    else
        # Placeholder when snapshot doesn't exist yet
        cat <<'EOF'
# CONTEXT SNAPSHOT (AUTO)
Updated: (not yet created)

## Status
- CONTEXT_SNAPSHOT.md does not exist yet.
- The Stop hook will create/update this file after each response.
- This is expected on first run.

## Action Required
- None. The Stop hook will auto-generate this file.
EOF
    fi
}

# --- MAIN ---

# Check if CLAUDE.md exists
if [[ ! -f "$CLAUDE_MD" ]]; then
    echo "[HOOK ERROR] CLAUDE.md not found at: $CLAUDE_MD" >&2
    exit 0  # Don't block on missing file, just warn
fi

# Output injected context (Claude Code adds this to conversation context)
echo "--- INJECTED CLAUDE.MD RULES (IMMUTABLE BLOCK) ---"
extract_immutable
echo "--- END INJECTED RULES ---"

echo ""
echo "--- CURRENT PROJECT CONTEXT SNAPSHOT ---"
inject_snapshot
echo "--- END CONTEXT SNAPSHOT ---"
