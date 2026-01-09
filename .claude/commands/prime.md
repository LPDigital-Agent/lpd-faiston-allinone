---
name: prime
description: Prime Claude Code context (rules + product + code) after /clear
allowed-tools: Read, Bash, Glob, Grep
---

# Context Prime — Faiston NEXO

Purpose: After `/clear`, reload **rules**, **what is being built**, and **where the code lives**, without bloating memory.

---

## Phase 0: Hard Reset (MANDATORY)

This command assumes `/clear` was just executed.
If not, STOP and run `/clear` first.

---

## Phase 1: Global Rules (MANDATORY)

### Load `CLAUDE.md` (Source of Truth)

```bash
cat CLAUDE.md
```

Rules are NOT duplicated here.
CLAUDE.md is the only source of truth for architecture, infra, security, and AI policies.

---

## Phase 2: Product Context (MANDATORY)

### Product Definition

| Field              | Value                                    |
| ------------------ | ---------------------------------------- |
| **Product**        | Faiston NEXO                             |
| **Type**           | AI-First, 100% Agentic Intranet Platform |
| **AI Orchestrator**| NEXO                                     |
| **Phase**          | Phase 1 — Foundation                     |

### Load PRD (Preview Only)

```bash
cat product-development/current-feature/PRD.md | head -120
```

If deeper requirements are needed, open the PRD fully on demand.

---

## Phase 3: Codebase Orientation (MANDATORY)

### High-Level Repository Map (NO DUMPS)

```bash
ls -la
```

**Key areas:**

| Directory      | Purpose                                  |
| -------------- | ---------------------------------------- |
| `client/`      | Next.js 15 frontend (App Router)         |
| `server/`      | Google ADK + Bedrock AgentCore agents    |
| `terraform/`   | ALL AWS infrastructure (Terraform only)  |
| `docs/`        | Documentation                            |
| `.claude/`     | Claude Code commands and skills          |

### AgentCore Runtimes

| Runtime                | Agents     | Purpose                   |
| ---------------------- | ---------- | ------------------------- |
| `agentcore-inventory`  | 15 agents  | SGA - Gestão de Estoque   |
| `agentcore-academy`    | 11 agents  | Hive Academy - Learning   |
| `agentcore-portal`     | 3 agents   | NEXO Orchestrator         |

### Minimal Tree (2 levels max)

```bash
tree -L 2 -I 'node_modules|dist|.git|.next' . | head -40
```

---

## Phase 4: Current Work Context (MANDATORY)

```bash
git branch --show-current
git status --short
git log --oneline -5
```

This defines what is currently in progress.

---

## Phase 5: Architecture Snapshot (CONCEPTUAL)

```text
Frontend (Next.js 15)
  └── AWS Cognito + Microsoft Entra
        └── AWS Bedrock AgentCore
              ├── Runtime (Google ADK agents)
              ├── Memory (STM + LTM)
              └── Gateway (MCP tools)
```

Detailed diagrams live in `docs/architecture/`.

---

## Phase 6: Optional Memory (ON DEMAND)

Use AgentCore Memory resources ONLY if required by the task.

**Memory IDs (Provisioned in AWS):**

| Memory ID | Runtime | Purpose |
|-----------|---------|---------|
| `nexo_agent_mem-Z5uQr8CDGf` | agentcore-inventory | Smart Import episodic learning |
| `faiston_academy_agents_mem-DNh4D14Rbv` | agentcore-academy | Academy STM conversation context |

Do NOT preload memory unnecessarily.

---

## Phase 7: Prime Complete (MANDATORY NEXT STEP)

Before writing any code:

1. Restate the key constraints from CLAUDE.md
2. State what you are about to build or change
3. Create a PLAN
4. Only then implement

---

## PRIME AUDIT RULE (MANDATORY)

`/prime` MUST stay lightweight.

**NOT allowed here:**

- Large file lists
- Sprint logs
- Changelogs
- Component inventories
- Full architecture documents

If more detail is needed → open the specific document or module `CLAUDE.md`.
