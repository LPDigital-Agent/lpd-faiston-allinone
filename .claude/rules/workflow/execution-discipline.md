# Execution Discipline Rules

> These workflow rules apply globally to all development tasks.

## Context First

- First THINK through the problem
- READ the codebase (relevant files) before proposing solutions
- NEVER speculate about code you haven't opened

## Major Changes Require Approval

Before ANY major change (architecture, refactor, broad behavior change):
1. Check in with user
2. Get EXPLICIT approval of the plan
3. Document the approach

## High-Level Change Summary

At every step, provide:
- SHORT explanation of what changed
- WHY it changed
- NO long essays

## Simplicity First

- Keep every task/change as SIMPLE as possible
- Avoid massive or complex changes
- Each change should impact as little code as possible

## Architecture Documentation

- Maintain documentation describing application architecture end-to-end
- Keep it updated when architecture changes
- Location: `docs/`

## Primary Instructions

- NEVER create files in root unless absolutely necessary
- ALL documentation lives in `docs/`
- Be extremely concise
- ALWAYS create a PLAN before implementation

## Git & GitHub

- Use GitHub CLI
- Branch prefix: `fabio/`

## SubAgents & Skills

- ALWAYS use Claude Code SubAgents and Skills in all tasks/debugs
- Use `prompt-engineer` SubAgent to improve prompts
- SubAgents are NOT optional—use by default for parallel execution

## Tooling Enforcement

- For EVERY development task, MUST use SubAgents, Skills, and consult required MCP sources
- Required sources: Context7, AWS Documentation, Bedrock AgentCore, Terraform MCP
- If proceeding without SubAgents/MCP checks → STOP and ask for approval
