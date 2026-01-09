---
allowed-tools: Bash(git checkout:*), Bash(git branch:*), Bash(git status:*), Bash(git pull:*), Bash(git fetch:*)
argument-hint: <branch-name> | --from <base-branch>
description: Create feature branch with fabio/ prefix convention
---

# Create Feature Branch

Create branch: $ARGUMENTS

## Current State

- Current branch: !`git branch --show-current`
- Git status: !`git status --porcelain | head -5`
- Recent branches: !`git branch --sort=-committerdate | head -5`

## What This Command Does

Creates a new feature branch following the team convention:

1. **Prefix**: All branches get `fabio/` prefix automatically
2. **Format**: Converts input to kebab-case if needed
3. **Base**: Creates from `main` by default (or specified base)
4. **Switch**: Automatically checks out the new branch

## Branch Naming Convention

```
fabio/<type>-<description>

Examples:
  fabio/add-user-auth
  fabio/fix-login-bug
  fabio/refactor-api-client
  fabio/feat-dark-mode
```

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: /branch add-user-auth                               │
├─────────────────────────────────────────────────────────────┤
│  1. Check for uncommitted changes                           │
│     └── If dirty: warn user, ask to stash or commit         │
│                                                             │
│  2. Fetch latest from origin                                │
│     └── git fetch origin                                    │
│                                                             │
│  3. Create branch from main (or specified base)             │
│     └── git checkout -b fabio/add-user-auth main            │
│                                                             │
│  4. Confirm creation                                        │
│     └── "✅ Created and switched to fabio/add-user-auth"    │
└─────────────────────────────────────────────────────────────┘
```

## Command Options

- `<branch-name>`: Required. The branch name (prefix added automatically)
- `--from <base>`: Optional. Create from a specific branch instead of main

## Examples

```bash
# Basic usage - creates fabio/add-user-auth from main
/branch add-user-auth

# With type prefix
/branch feat-dark-mode
/branch fix-login-bug
/branch refactor-api

# From a different base branch
/branch hotfix-urgent --from release/v2.0

# Auto-formats names (spaces/underscores → kebab-case)
/branch "add user auth"  → fabio/add-user-auth
/branch add_user_auth    → fabio/add-user-auth
```

## Input Transformations

| Input | Output |
|-------|--------|
| `add user auth` | `fabio/add-user-auth` |
| `add_user_auth` | `fabio/add-user-auth` |
| `AddUserAuth` | `fabio/add-user-auth` |
| `fabio/something` | `fabio/something` (no double prefix) |

## Safety Checks

1. **Uncommitted changes**: Warns if working directory is dirty
2. **Branch exists**: Checks if branch already exists locally or remotely
3. **Base branch**: Verifies base branch exists before creating

## Important Notes

- Always creates from latest `main` (fetches first)
- If branch already exists, offers to switch to it instead
- Does NOT push the branch — use `/ship` when ready
- Follows CLAUDE.md convention: `fabio/` prefix for all feature branches
