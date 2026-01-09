---
allowed-tools: Bash(pnpm:*), Bash(npm:*), Bash(cd:*)
argument-hint: [--skip-tests] | [--skip-lint] | [--skip-build]
description: Pre-ship validation - runs lint, build, and tests with pass/fail summary
---

# Pre-Ship Validation Check

Run validation checks: $ARGUMENTS

## Current State

- Working directory: !`pwd`
- Git status: !`git status --porcelain | head -10`
- Current branch: !`git branch --show-current`

## What This Command Does

Runs a complete validation pipeline before shipping code:

1. **Lint** (`pnpm lint`) — Check code quality and style
2. **Build** (`pnpm build`) — Verify TypeScript compiles and build succeeds
3. **Tests** (`pnpm test`) — Run test suite (if exists)

## Execution Order

```
┌─────────────────────────────────────────────────────────────┐
│  1. LINT                                                    │
│     pnpm lint                                               │
│     ├── ✅ Pass → Continue to Build                        │
│     └── ❌ Fail → Show errors, STOP                        │
├─────────────────────────────────────────────────────────────┤
│  2. BUILD                                                   │
│     pnpm build                                              │
│     ├── ✅ Pass → Continue to Tests                        │
│     └── ❌ Fail → Show errors, STOP                        │
├─────────────────────────────────────────────────────────────┤
│  3. TESTS (if test script exists)                          │
│     pnpm test                                               │
│     ├── ✅ Pass → All checks passed!                       │
│     └── ❌ Fail → Show failures, STOP                      │
└─────────────────────────────────────────────────────────────┘
```

## Command Options

- `--skip-tests`: Skip test execution (lint + build only)
- `--skip-lint`: Skip linting (build + tests only)
- `--skip-build`: Skip build (lint + tests only)

## Output Format

After running, provide a summary table:

```
┌────────────────────────────────────────┐
│           VALIDATION SUMMARY           │
├──────────────┬─────────┬───────────────┤
│ Check        │ Status  │ Time          │
├──────────────┼─────────┼───────────────┤
│ Lint         │ ✅ PASS │ 2.3s          │
│ Build        │ ✅ PASS │ 45.2s         │
│ Tests        │ ✅ PASS │ 12.1s         │
├──────────────┴─────────┴───────────────┤
│ 🚀 ALL CHECKS PASSED - Ready to ship!  │
└────────────────────────────────────────┘
```

Or on failure:

```
┌────────────────────────────────────────┐
│           VALIDATION SUMMARY           │
├──────────────┬─────────┬───────────────┤
│ Check        │ Status  │ Time          │
├──────────────┼─────────┼───────────────┤
│ Lint         │ ✅ PASS │ 2.3s          │
│ Build        │ ❌ FAIL │ 12.4s         │
│ Tests        │ ⏭️ SKIP │ -             │
├──────────────┴─────────┴───────────────┤
│ ❌ BLOCKED - Fix build errors first    │
└────────────────────────────────────────┘
```

## Workflow

1. Navigate to project root (client/ directory for frontend checks)
2. Run each check in sequence
3. Stop on first failure and show error details
4. Provide actionable fix suggestions when possible
5. Show final summary table

## Important Notes

- This command runs in the `client/` directory by default for frontend validation
- If running from root, checks both client and server if applicable
- Failed checks BLOCK the pipeline — fix errors before shipping
- Use `--skip-*` flags only when you have a good reason
