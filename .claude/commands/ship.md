---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git diff:*), Bash(git log:*), Bash(git push:*), Bash(git remote:*), Bash(git branch:*)
argument-hint: [message] | --force | --no-verify
description: Commit all changes and push to GitHub in one command
---

# Ship to GitHub

Commit and push all changes: $ARGUMENTS

## Current Repository State

- Git status: !`git status --porcelain`
- Current branch: !`git branch --show-current`
- Remote tracking: !`git remote -v | head -2`
- Staged changes: !`git diff --cached --stat`
- Unstaged changes: !`git diff --stat`
- Recent commits: !`git log --oneline -3`

## What This Command Does

1. Checks current git status and branch
2. If no files are staged, automatically stages ALL modified and new files with `git add -A`
3. Analyzes the diff to generate an appropriate commit message
4. Creates a commit using emoji conventional commit format
5. Pushes the commit to the remote repository (origin)
6. If the branch has no upstream, sets it with `git push -u origin <branch>`

## Commit Message Format

Use emoji conventional commit format:
- ✨ `feat`: New feature
- 🐛 `fix`: Bug fix
- 📝 `docs`: Documentation
- 💄 `style`: Formatting/style
- ♻️ `refactor`: Code refactoring
- ⚡️ `perf`: Performance improvements
- ✅ `test`: Tests
- 🔧 `chore`: Tooling, configuration
- 🚀 `ci`: CI/CD improvements
- 🔒️ `fix`: Security fixes
- 🏗️ `refactor`: Architectural changes

## Command Options

- `[message]`: Optional custom commit message (skips auto-generation)
- `--force`: Force push (use with caution!)
- `--no-verify`: Skip pre-commit hooks

## Workflow

```
1. git add -A                    # Stage all changes
2. git commit -m "<message>"     # Commit with emoji conventional format
3. git push origin <branch>      # Push to remote
```

## Safety Rules

- NEVER force push to `main` or `master` without explicit confirmation
- ALWAYS verify the diff before committing
- If push fails due to remote changes, suggest `git pull --rebase` first

## Examples

```bash
# Auto-generate commit message and push
/ship

# Custom commit message
/ship "feat: add user dashboard"

# Force push (be careful!)
/ship --force

# Skip hooks
/ship --no-verify
```

## Important Notes

- This command stages ALL changes (tracked and untracked files)
- If you only want to commit specific files, stage them manually first with `git add`
- The push will fail if there are upstream changes - pull first in that case
- Branch prefix convention: `fabio/` for feature branches
