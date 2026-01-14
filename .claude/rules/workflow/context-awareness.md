# Context Awareness & Impact Analysis

> YOU MUST NOT CHANGE ANYTHING without first fully understanding it.

## Before Any Change

You MUST understand:
- **WHAT** you are changing
- **WHY** it exists
- **HOW** it is used
- **WHERE** it is referenced
- **WHAT** other systems/modules/commands may be affected

## Forbidden Behavior

- Making changes "to improve" without understanding context
- Refactoring/simplifying without impact analysis
- Changing commands (`prime`, `sync-project`, etc.) without understanding original purpose
- Assuming intent instead of reading documentation and code
- Changing behavior because "it seems better"

## Mandatory Steps Before Any Change

1. Read relevant documentation (CLAUDE.md, prime.md, sync-project.md, docs/)
2. Understand the ORIGINAL INTENT of code or rule
3. Identify ALL dependencies and side effects
4. State explicitly what WILL change and what will NOT change
5. Only then implement

## Rule of Thumb

If you cannot clearly explain **why something was built the way it is**, you are **NOT ALLOWED** to change it.

## Enforcement

If a change was made without proper context understanding or impact analysis:
- Consider it **INVALID**
- Revert if necessary
- **STOP AND ASK FOR GUIDANCE** before proceeding
