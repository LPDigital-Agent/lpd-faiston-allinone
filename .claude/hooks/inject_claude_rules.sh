#!/usr/bin/env bash
# inject_claude_rules.sh - Injects IMMUTABLE rules from CLAUDE.md into Claude Code context
# Hook: UserPromptSubmit
# Purpose: Ensure critical rules are always fresh in context before processing prompts

set -euo pipefail

# Use project directory from Claude Code env var, fallback to script location
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
CLAUDE_MD="${PROJECT_DIR}/CLAUDE.md"

# Check if CLAUDE.md exists
if [[ ! -f "$CLAUDE_MD" ]]; then
    echo "[HOOK ERROR] CLAUDE.md not found at: $CLAUDE_MD" >&2
    exit 0  # Don't block on missing file, just warn
fi

# Extract IMMUTABLE block (lines 13-488) or fallback to first 160 lines
# The IMMUTABLE block is between the comment markers
extract_immutable() {
    # Try to extract lines 13-488 (the IMMUTABLE block)
    if sed -n '13,488p' "$CLAUDE_MD" 2>/dev/null | grep -q "IMMUTABLE"; then
        sed -n '13,488p' "$CLAUDE_MD"
    else
        # Fallback: first 160 lines
        head -160 "$CLAUDE_MD"
    fi
}

# Output the rules (Claude Code will inject this as context)
echo "--- INJECTED CLAUDE.MD RULES (IMMUTABLE BLOCK) ---"
extract_immutable
echo "--- END INJECTED RULES ---"
