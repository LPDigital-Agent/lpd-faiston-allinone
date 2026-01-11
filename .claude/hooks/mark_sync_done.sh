#!/usr/bin/env bash
# mark_sync_done.sh - Write timestamp marker when /sync-project completes
# Called by: sync-project.md Stop hook
# Creates: .claude/hooks_state/last_sync_project.utc
set -euo pipefail

STATE_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks_state"
mkdir -p "$STATE_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "${TIMESTAMP} sha=${GIT_SHA}" > "$STATE_DIR/last_sync_project.utc"
