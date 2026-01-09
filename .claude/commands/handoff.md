# Handoff Command

Generate a comprehensive handoff prompt for the next AI agent session.

## Instructions

Create a handoff prompt that includes:

1. **Global Context** - Repository, project, and current objective
2. **What Was Accomplished** - Summary of completed work this session
3. **Pending Tasks** - Table format with status and notes
4. **Key Files** - Files modified/created with line numbers where relevant
5. **AWS Environment** - Account, region, resource identifiers

## Requirements for the Handoff Prompt

The prompt you generate MUST instruct the next agent to:

1. **Use subagents** whenever possible to save context and parallelize work
2. **Read any local task trackers** (*.local.md files) first
3. **Determine what still needs to be done** by checking git status, reading files
4. **Return a plan in TABULAR FORMAT** pending user approval before taking action
5. **Ask for fresh AWS credentials** if needed

## Format

```markdown
# Session Handoff: [Task Title]

## Global Context
[Brief description of repo, project, objective]

**IMPORTANT**: Use subagents whenever possible to save context and parallelize work.

---

## What Was Accomplished This Session
[Numbered list of completed items]

---

## Pending Tasks
| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | ... | PENDING | ... |

---

## Instructions
1. First, read [relevant files]
2. Run `git status` to see uncommitted changes
3. Determine what still needs to be done
4. Return a plan in TABULAR FORMAT pending user approval
5. Use SUBAGENTS when possible

---

## Key Files
- `path/to/file` - Description (lines X-Y)

---

## AWS Environment
- Account: ...
- Region: ...
- [Other relevant resources]
```

## Example Usage

User: "/handoff"
Agent: [Generates handoff prompt based on current session context]
