#!/usr/bin/env python3
"""
post_turn_update.py - Updates CONTEXT_SNAPSHOT.md and WORKLOG.md after each Claude Code response
Hook: Stop
Purpose: Maintain continuous context (snapshot) and audit trail (worklog)

BEHAVIOR:
1. Updates docs/CONTEXT_SNAPSHOT.md (OVERWRITE with fixed format)
2. Appends to docs/WORKLOG.md (APPEND audit entry)
3. BLOCKS if update fails (unless CLAUDE_HOOKS_ALLOW_FAIL=true)

CONTEXT_SNAPSHOT FORMAT (strict ~30 lines):
  - Current Goal
  - Current Plan (Next 3 Steps)
  - Last Turn Summary
  - Active Constraints
  - Risks / Blockers
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# --- CONSTANTS ---
MAX_SUMMARY_LEN = 240  # For snapshot summaries
MAX_WORKLOG_LEN = 1200  # For worklog entries
ACTIVE_CONSTRAINTS = [
    "AI-FIRST / AGENTIC architecture only (no traditional microservices)",
    "AWS Bedrock AgentCore for all agents",
    "Terraform only (no CloudFormation/SAM)",
    "Amazon Cognito for auth (no Amplify)",
    "Aurora PostgreSQL for inventory (no DynamoDB)",
    "Python 3.13 + arm64 for all Lambdas",
]


# --- UTILITY FUNCTIONS ---
def log_error(msg: str) -> None:
    """Log to stderr (visible in Claude Code logs)."""
    print(f"[HOOK ERROR] {msg}", file=sys.stderr)


def log_info(msg: str) -> None:
    """Log info to stderr."""
    print(f"[HOOK INFO] {msg}", file=sys.stderr)


def block_response(reason: str) -> None:
    """Output blocking JSON to stdout and exit."""
    response = {
        "decision": "block",
        "reason": f"Post-turn context update failed: {reason}. Fix hooks or set CLAUDE_HOOKS_ALLOW_FAIL=true temporarily."
    }
    print(json.dumps(response))
    sys.exit(0)


def allow_fail() -> bool:
    """Check if we should allow failures (escape hatch)."""
    return os.environ.get("CLAUDE_HOOKS_ALLOW_FAIL", "").lower() == "true"


def truncate(text: str, max_len: int) -> str:
    """Truncate text to max length with ellipsis."""
    text = text.strip().replace("\n", " ")  # Normalize
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


# --- TRANSCRIPT PARSING ---
def extract_text_from_message(message: dict) -> str:
    """Extract text content from a transcript message."""
    content = message.get("content", [])
    if isinstance(content, str):
        return content

    # Handle content array (common in Claude responses)
    texts = []
    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif "text" in item:
                texts.append(item["text"])
        elif isinstance(item, str):
            texts.append(item)

    return " ".join(texts).strip()


def parse_transcript(transcript_path: str) -> tuple[str, str]:
    """
    Parse JSONL transcript to extract latest user and assistant messages.
    Returns (user_text, assistant_text).
    """
    user_text = ""
    assistant_text = ""

    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                role = entry.get("role", "")

                if role == "user":
                    text = extract_text_from_message(entry)
                    if text:  # Only update if non-empty
                        user_text = text
                elif role == "assistant":
                    text = extract_text_from_message(entry)
                    if text:  # Only update if non-empty
                        assistant_text = text
            except json.JSONDecodeError:
                continue

    return user_text, assistant_text


# --- CONTEXT SNAPSHOT UPDATE ---
def infer_goal_from_text(user_text: str) -> str:
    """Infer current goal from user message."""
    if not user_text:
        return "TBD - no user message captured"
    # Take first sentence or first 100 chars
    first_sentence = user_text.split(".")[0].strip()
    if len(first_sentence) > 100:
        first_sentence = first_sentence[:97] + "..."
    return first_sentence or "TBD"


def write_context_snapshot(project_dir: str, user_text: str, assistant_text: str) -> str:
    """
    Write CONTEXT_SNAPSHOT.md with fixed format.
    Returns timestamp for verification.
    """
    snapshot_path = Path(project_dir) / "docs" / "CONTEXT_SNAPSHOT.md"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Infer content
    goal = infer_goal_from_text(user_text)
    user_summary = truncate(user_text, MAX_SUMMARY_LEN) if user_text else "(no user message captured)"
    assistant_summary = truncate(assistant_text, MAX_SUMMARY_LEN) if assistant_text else "(no assistant response captured)"

    # Build snapshot with fixed format
    constraints_bullets = "\n".join(f"- {c}" for c in ACTIVE_CONSTRAINTS)

    content = f"""# CONTEXT SNAPSHOT (AUTO)
Updated: {timestamp}

## Current Goal
- {goal}

## Current Plan (Next 3 Steps)
1. Continue with current task
2. Validate changes
3. Test and verify

## Last Turn Summary
- User: {user_summary}
- Assistant: {assistant_summary}

## Active Constraints (from CLAUDE.md)
{constraints_bullets}

## Risks / Blockers
- None identified
"""

    snapshot_path.write_text(content, encoding="utf-8")
    return timestamp


# --- WORKLOG UPDATE ---
def write_worklog_entry(project_dir: str, user_text: str, assistant_text: str) -> str:
    """
    Append entry to WORKLOG.md.
    Returns timestamp for verification.
    """
    worklog_path = Path(project_dir) / "docs" / "WORKLOG.md"
    worklog_path.parent.mkdir(parents=True, exist_ok=True)

    # Create file with header if it doesn't exist
    if not worklog_path.exists():
        header = "# Work Log\n\nAutomatically maintained by Claude Code hooks.\n\n---\n\n"
        worklog_path.write_text(header, encoding="utf-8")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    user_summary = truncate(user_text, MAX_WORKLOG_LEN) if user_text else "(no user message captured)"
    assistant_summary = truncate(assistant_text, MAX_WORKLOG_LEN) if assistant_text else "(no assistant response captured)"

    entry = f"""## Turn Log — {timestamp}

**User:** {user_summary}

**Assistant:** {assistant_summary}

---

"""

    with open(worklog_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return timestamp


# --- VERIFICATION ---
def verify_snapshot(project_dir: str, timestamp: str) -> bool:
    """Verify CONTEXT_SNAPSHOT.md was updated successfully."""
    snapshot_path = Path(project_dir) / "docs" / "CONTEXT_SNAPSHOT.md"
    if not snapshot_path.exists():
        return False
    content = snapshot_path.read_text(encoding="utf-8")
    return timestamp in content


def verify_worklog(project_dir: str, timestamp: str) -> bool:
    """Verify WORKLOG.md was updated successfully."""
    worklog_path = Path(project_dir) / "docs" / "WORKLOG.md"
    if not worklog_path.exists():
        return False
    content = worklog_path.read_text(encoding="utf-8")
    return timestamp in content


# --- MAIN ---
def main() -> None:
    # Read JSON payload from stdin
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        if allow_fail():
            log_error(f"Failed to parse stdin JSON: {e}")
            return
        block_response(f"Invalid JSON from stdin: {e}")
        return

    # Check for recursion guard (CRITICAL: prevents infinite loops)
    if payload.get("stop_hook_active", False):
        return  # Exit silently

    transcript_path = payload.get("transcript_path", "")

    if not transcript_path:
        if allow_fail():
            log_error("No transcript_path in payload")
            return
        block_response("No transcript_path provided in hook payload")
        return

    # Get project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        project_dir = str(Path(__file__).parent.parent.parent)

    # Parse transcript
    try:
        user_text, assistant_text = parse_transcript(transcript_path)
    except FileNotFoundError:
        if allow_fail():
            log_error(f"Transcript file not found: {transcript_path}")
            return
        block_response(f"Transcript file not found: {transcript_path}")
        return
    except Exception as e:
        if allow_fail():
            log_error(f"Failed to parse transcript: {e}")
            return
        block_response(f"Transcript parse error: {e}")
        return

    # Update CONTEXT_SNAPSHOT.md (OVERWRITE)
    try:
        snapshot_timestamp = write_context_snapshot(project_dir, user_text, assistant_text)
    except Exception as e:
        if allow_fail():
            log_error(f"Failed to write CONTEXT_SNAPSHOT.md: {e}")
            return
        block_response(f"CONTEXT_SNAPSHOT write failed: {e}")
        return

    # Verify snapshot write
    if not verify_snapshot(project_dir, snapshot_timestamp):
        if allow_fail():
            log_error("CONTEXT_SNAPSHOT.md verification failed")
            return
        block_response("CONTEXT_SNAPSHOT write verification failed")
        return

    # Update WORKLOG.md (APPEND)
    try:
        worklog_timestamp = write_worklog_entry(project_dir, user_text, assistant_text)
    except Exception as e:
        if allow_fail():
            log_error(f"Failed to write WORKLOG.md: {e}")
            return
        block_response(f"WORKLOG write failed: {e}")
        return

    # Verify worklog write
    if not verify_worklog(project_dir, worklog_timestamp):
        if allow_fail():
            log_error("WORKLOG.md verification failed")
            return
        block_response("WORKLOG write verification failed")
        return

    # Success
    log_info(f"Context updated: CONTEXT_SNAPSHOT.md + WORKLOG.md @ {snapshot_timestamp}")


if __name__ == "__main__":
    main()
