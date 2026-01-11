#!/usr/bin/env python3
"""
post_turn_memory.py - Updates WORKLOG.md after each Claude Code response
Hook: Stop
Purpose: Maintain running record of work and decisions with HARDCORE blocking on failure

HARDCORE MODE: If WORKLOG update fails, this hook BLOCKS the stop (decision: "block")
Escape hatch: Set CLAUDE_HOOKS_ALLOW_FAIL=true to disable blocking
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def log_error(msg: str) -> None:
    """Log to stderr (visible in Claude Code logs)."""
    print(f"[HOOK ERROR] {msg}", file=sys.stderr)


def block_response(reason: str) -> None:
    """Output blocking JSON to stdout and exit."""
    response = {
        "decision": "block",
        "reason": f"WORKLOG update failed: {reason}. Fix hooks or disable block mode."
    }
    print(json.dumps(response))
    sys.exit(0)


def allow_fail() -> bool:
    """Check if we should allow failures (escape hatch)."""
    return os.environ.get("CLAUDE_HOOKS_ALLOW_FAIL", "").lower() == "true"


def truncate(text: str, max_len: int = 1200) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


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
                    user_text = extract_text_from_message(entry)
                elif role == "assistant":
                    assistant_text = extract_text_from_message(entry)
            except json.JSONDecodeError:
                continue

    return user_text, assistant_text


def write_worklog_entry(project_dir: str, user_text: str, assistant_text: str) -> str:
    """
    Append entry to WORKLOG.md.
    Returns timestamp for verification.
    """
    worklog_path = Path(project_dir) / "docs" / "WORKLOG.md"

    # Ensure docs directory exists
    worklog_path.parent.mkdir(parents=True, exist_ok=True)

    # Create file with header if it doesn't exist
    if not worklog_path.exists():
        header = "# Work Log\n\nAutomatically maintained by Claude Code hooks.\n\n---\n\n"
        worklog_path.write_text(header, encoding="utf-8")

    # Generate entry
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    user_summary = truncate(user_text) if user_text else "(no user message captured)"
    assistant_summary = truncate(assistant_text) if assistant_text else "(no assistant response captured)"

    entry = f"""## {timestamp}

**User asked:** {user_summary}

**Assistant did:** {assistant_summary}

---

"""

    # Append to file
    with open(worklog_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return timestamp


def verify_write(project_dir: str, timestamp: str) -> bool:
    """Verify WORKLOG.md was updated successfully."""
    worklog_path = Path(project_dir) / "docs" / "WORKLOG.md"

    if not worklog_path.exists():
        return False

    content = worklog_path.read_text(encoding="utf-8")
    return timestamp in content


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

    # Check for recursion guard
    if payload.get("stop_hook_active", False):
        # Exit silently to avoid infinite loop
        return

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
        # Fallback: derive from script location
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

    # Write to WORKLOG.md
    try:
        timestamp = write_worklog_entry(project_dir, user_text, assistant_text)
    except Exception as e:
        if allow_fail():
            log_error(f"Failed to write WORKLOG.md: {e}")
            return
        block_response(f"Write failed: {e}")
        return

    # Verify write
    if not verify_write(project_dir, timestamp):
        if allow_fail():
            log_error("WORKLOG.md verification failed")
            return
        block_response("Write verification failed - timestamp not found")
        return

    # Success - no output needed (non-blocking)
    log_error(f"WORKLOG.md updated: {timestamp}")  # Informational log


if __name__ == "__main__":
    main()
