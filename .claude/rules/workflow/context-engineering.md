# Context Engineering Rules

> Based on Anthropic's Context Engineering Guide and Claude Code Best Practices (2025-2026).

## Token Efficiency

- Context is a **FINITE RESOURCE** — every token competes for attention
- Prefer **pointers to copies**: Use `file:line` references, not code snippets
- Use **progressive disclosure**: Load context just-in-time, not upfront
- If context exceeds **60% capacity** → `/compact` or `/clear` + `/prime`

## Instruction Limits

- LLMs can follow ~150-200 instructions with reasonable consistency
- This CLAUDE.md already contains ~50+ instructions
- **DO NOT** add task-specific instructions to root CLAUDE.md
- **DO** add task-specific guidance in `docs/` and reference with `@docs/filename.md`

## Structure Principle

- Follow **WHAT** (tech stack) / **WHY** (purpose) / **HOW** (process) model
- Use clear section headers
- Separate instructions from context

## Tool Delegation

- **NEVER** send an LLM to do a linter's job → Use Biome, ESLint, ruff
- Use `/check` skill for lint + build + test validation
- Reserve AI for reasoning tasks, not mechanical validation

## Uncertainty Handling

- **EXPRESS UNCERTAINTY** rather than guessing → reduces hallucinations
- If unsure → **READ MORE FILES** before proceeding
- If still unsure → **ASK THE USER**

## Context Window Management

When context exceeds ~60%:
1. STOP
2. Re-read CLAUDE.md
3. Restate active constraints and current PLAN
4. Use `/compact` to preserve decisions
5. If needed, `/clear` then `/prime`

## Compaction Workflow

- Before `/compact` → run `/sync-project` FIRST
- After compaction → re-run `/prime`
- If `/sync-project` not executed before compaction → BLOCK compaction

## Compaction Strategy

When nearing context limits:
- **Preserve:** architectural decisions, unresolved issues
- **Discard:** redundant tool outputs, verbose logs
- Use structured notes (`NOTES.md`, `TODO.md`) for long tasks

## Hooks Enforcement

Claude Code Hooks MUST be enabled:
- `UserPromptSubmit`: Inject essential rules + current context from `docs/CONTEXT_SNAPSHOT.md`
- `Stop`: Update `docs/CONTEXT_SNAPSHOT.md` + append to `docs/WORKLOG.md`
- Hook details in `docs/Claude Code/HOOKS.md`

## Flywheel Improvement

Treat CLAUDE.md as a living document:
- Review logs for common mistakes → Update rules
- Pattern: Bugs → Improved CLAUDE.md/Skills → Better Agent

**Adding New Rules:**
1. Identify recurring mistake/pattern
2. Propose rule with justification
3. Add to appropriate section (NOT root if module-specific)
4. Test effectiveness over 3+ sessions

**Forbidden:**
- Adding rules without observed need
- Adding code snippets (use file:line references)
- Adding task-specific instructions to root CLAUDE.md
