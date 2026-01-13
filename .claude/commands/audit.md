# Code Compliance Audit

**Role:** Staff Engineer and Senior Code Quality Auditor
**Objective:** Analyze provided files and validate them strictly against the rules defined in the project's `CLAUDE.md`.

## Target

Audit target: **$ARGUMENTS**

## Current Context

- Working directory: !`pwd`
- Git branch: !`git branch --show-current`
- Last commit: !`git log --oneline -1`

---

## Analysis Instructions

### Phase 1: Load Rules

1. Read and internalize all rules from `CLAUDE.md` at the project root
2. Pay special attention to:
   - **IMMUTABLE BLOCK** rules (non-negotiable)
   - Infrastructure policies (Terraform, AWS)
   - Architecture constraints (AI-First, Agentic, Strands Agents)
   - LLM Policy (Gemini 3 family only)
   - Authentication policy (Cognito, no Amplify)
   - Memory model (AgentCore Memory)
   - Code quality standards (Clean Code, SOLID, DRY)

### Phase 2: Analyze Code

1. Read all files specified in `$ARGUMENTS`
2. For each file, check for violations against:
   - **CLAUDE.md explicit rules** — Primary focus
   - **Universal best practices** — SOLID, DRY, KISS, YAGNI
   - **Security vulnerabilities** — OWASP Top 10
   - **Type safety** — Proper TypeScript/Python typing
   - **Naming conventions** — Consistent and descriptive
   - **Error handling** — Proper try/catch, error boundaries

### Phase 3: Generate Report

**CRITICAL:** Do NOT hallucinate issues. Only report violations that:
- Explicitly violate a rule in `CLAUDE.md`, OR
- Clearly violate universal engineering best practices

If the code is clean, say so. A good audit finds real problems, not imaginary ones.

---

## Output Format

Generate a clean Markdown report with the following structure:

```markdown
# 🕵️ Code Compliance Audit Report

**Audited:** [files/paths audited]
**Date:** [timestamp]
**Auditor:** Claude Code (Staff Engineer Mode)

---

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Status** | [✅ APPROVED / ❌ REJECTED / ⚠️ NEEDS REVIEW] |
| **Quality Score** | [0-10] |
| **Critical Issues** | [count] |
| **Medium Issues** | [count] |
| **Minor Issues** | [count] |

---

## 🔴 Critical Issues (Blockers)

*Severe violations that break architecture, security, or prevent build/deploy.*

### Issue 1: [Short Title]

* **File:** `path/to/file.ts:42`
* **Severity:** 🔴 CRITICAL
* **Category:** [Architecture / Security / Build / Compliance]
* **Description:** [Clear explanation of what's wrong]
* **Rule Violated:**
  > "[Exact quote from CLAUDE.md]"
* **Current Code:**
  ```typescript
  // problematic code snippet
  ```
* **Suggested Fix:**
  ```typescript
  // corrected code snippet
  ```

---

## 🟡 Medium Issues (Tech Debt)

*Violations of naming standards, missing tests, weak typing, or pattern inconsistencies.*

### Issue 1: [Short Title]

* **File:** `path/to/file.ts:15`
* **Severity:** 🟡 MEDIUM
* **Category:** [Typing / Testing / Naming / Patterns]
* **Description:** [What needs improvement]
* **Suggestion:** [How to fix it]

---

## 🟢 Minor Issues (Nitpicks)

*Style suggestions, readability improvements, or optional enhancements.*

* `file.ts:10` — Consider renaming `x` to `userCount` for clarity
* `file.ts:25` — Unused import can be removed
* `file.ts:50` — Magic number `86400` should be a named constant

---

## ✅ Compliance Checklist

| Rule Category | Status | Notes |
|---------------|--------|-------|
| Strands Agents Framework | ✅/❌ | [comment] |
| Gemini 3 LLM Policy | ✅/❌ | [comment] |
| AgentCore Memory Model | ✅/❌ | [comment] |
| Terraform Only (No CloudFormation) | ✅/❌ | [comment] |
| Cognito Auth (No Amplify) | ✅/❌ | [comment] |
| AI-First Architecture | ✅/❌ | [comment] |
| SOLID Principles | ✅/❌ | [comment] |
| Type Safety | ✅/❌ | [comment] |
| Error Handling | ✅/❌ | [comment] |

---

## 📋 Next Steps

1. **Immediate:** [List critical issues that must be fixed before merge]
2. **Short-term:** [List medium issues to address in this sprint]
3. **Backlog:** [List minor issues for future improvement]

---

*Audit completed. For questions, run `/audit` again with specific files.*
```

---

## Audit Workflow

1. **Parse Arguments:** Identify target files/directories from `$ARGUMENTS`
2. **Load Rules:** Read `CLAUDE.md` completely
3. **Analyze:** Check each file systematically
4. **Score:** Calculate quality score based on:
   - 10 = Perfect, no issues
   - 8-9 = Minor issues only
   - 6-7 = Some medium issues
   - 4-5 = Critical issues present
   - 0-3 = Severe architectural violations
5. **Report:** Generate the formatted report

---

## Important Guidelines

- **Be precise:** Quote exact file paths and line numbers
- **Be fair:** If code is good, acknowledge it
- **Be actionable:** Every issue must have a clear fix
- **Be honest:** If you're unsure about a rule, say so
- **Stay grounded:** Never invent violations that don't exist

---

## Example Usage

```bash
# Audit a single file
/audit server/agentcore-inventory/agents/nexo_import/agent.py

# Audit a directory
/audit client/src/components/

# Audit multiple targets
/audit server/agentcore-inventory/ client/src/lib/

# Audit recent changes
/audit $(git diff --name-only HEAD~1)
```
