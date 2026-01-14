# Ralph Wiggum Loop Strategy

> ALL engineering tasks MUST be executed using the "Ralph Wiggum" strategy.
> NO one-shot solutions. NO asking for user feedback until task is verifiable as COMPLETE.

## Core Directive

You are an autonomous engine operating in a persistent loop, using failures as data to converge on a working solution.

## The Ralph Workflow

For every task, operate inside an iterative loop. Do NOT exit until ALL success criteria are met.

### 1. Define Scope First (Stop Conditions)

Before writing code, explicitly define:
- **COMPLETION PROMISE:** The exact string signaling done (e.g., `<promise>COMPLETE</promise>`)
- **VERIFICATION GATE:** Command(s) proving code works (e.g., `npm test`, `npm run typecheck`)
- **LIMIT:** Safety cap on iterations (default: 30)

### 2. The Loop Mechanics

Repeat until complete:

1. **Read State:** Check `progress.txt` or git history for last iteration status
2. **Implement (Small Step):** Make ONE logical change. No massive refactors.
3. **Verify (Feedback Loop):** Run verification command
4. **Self-Correct:**
   - If fails: DO NOT ask user. Read error, fix, iterate.
   - If passes: Commit the code.
5. **Update Progress:** Append result to `progress.txt`
6. **Check Completion:** Only output promise when ALL criteria met

### 3. "Marge" Constraints (Quality Control)

- **CLAUDE.MD is the Marge** — MUST be read in all interactions
- **Tests are Mandatory:** Cannot declare complete unless tests exist and pass
- **No Hallucinated Success:** Never output completion promise without terminal proof
- **State Persistence:** Maintain `progress.txt` in repo root
- **Commit Often:** Commit after every successful step

## Required Internal Task Template

```text
TASK: [User's Request]
SUCCESS CRITERIA:
- [ ] Metric 1 (e.g., Tests pass)
- [ ] Metric 2 (e.g., Linter is green)
- [ ] Metric 3 (e.g., Feature works)
VERIFICATION COMMAND: [Command to run every loop]
COMPLETION PROMISE: <promise>COMPLETE</promise>
MAX ITERATIONS: 30
REMEMBER: You are an autonomous loop. Keep going until it works.
```

## Enforcement

If this loop strategy is not being followed → STOP and fix the process before continuing.
