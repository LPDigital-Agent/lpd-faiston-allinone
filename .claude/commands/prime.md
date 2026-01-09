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
| `client/`      | Next.js 16 + React 19 frontend (App Router) |
| `server/`      | Google ADK + Bedrock AgentCore agents    |
| `terraform/`   | ALL AWS infrastructure (Terraform only)  |
| `docs/`        | Documentation                            |
| `.claude/`     | Claude Code commands and skills          |

### AgentCore Runtimes (22 Total Agents)

| Runtime                | ID                                      | Agents     | Purpose                   |
| ---------------------- | --------------------------------------- | ---------- | ------------------------- |
| `agentcore-inventory`  | `faiston_asset_management-uSuLPsFQNH`   | 14 agents  | SGA - Inventory Management |
| `agentcore-academy`    | `faiston_academy_agents-ODNvP6HxCD`     | 6 agents   | Learning Platform          |
| `agentcore-portal`     | `faiston_portal_agents-PENDING`         | 2 agents   | NEXO Orchestrator          |

> **Key Docs:** `docs/AGENT_CATALOG.md` for full agent inventory, `docs/TROUBLESHOOTING.md` for HTTP 424 cold start issues.

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
Frontend (Next.js 16 + React 19)
  └── AWS Cognito (NO Amplify)
        └── AWS Bedrock AgentCore
              ├── Runtime (Google ADK agents: 14 inventory, 6 academy, 2 portal)
              ├── Memory (STM + LTM)
              └── Gateway (MCP tools)
```

Detailed diagrams live in `docs/architecture/`.

---

## Phase 5.5: Documentation Index (REFERENCE ONLY)

**Do NOT load these files during prime.** Reference them when needed for specific tasks.

### Core Documentation

| Document | When to Read |
|----------|--------------|
| `docs/AgentCore/IMPLEMENTATION_GUIDE.md` | AgentCore development, agent creation, cold start issues |
| `docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md` | SGA module patterns, hooks, contexts, agent flows |
| `docs/INFRASTRUCTURE.md` | AWS resources, Terraform, networking, security groups |

### Operations & Troubleshooting

| Document | When to Read |
|----------|--------------|
| `docs/TROUBLESHOOTING.md` | HTTP 424, auth errors, database issues, debugging |
| `docs/CI_CD_WORKFLOWS.md` | GitHub Actions, deployment, secrets configuration |
| `docs/DATABASE_SCHEMA.md` | Aurora PostgreSQL tables, DynamoDB design, migrations |

### Agent & API Reference

| Document | When to Read |
|----------|--------------|
| `docs/AGENT_CATALOG.md` | All 22 agents, their actions, tools, HIL routing |
| `docs/FRONTEND_AUTH.md` | Cognito auth, AgentCore Gateway JWT, token refresh |

### Product Requirements

| Document | When to Read |
|----------|--------------|
| `docs/prd_modulo_gestao_estoque_faiston_sga2.md` | SGA 2.0 PRD, requirements, KPIs |
| `docs/Faiston_Investory_Mamagement.md` | Strategic vision, As-Is/To-Be architecture |

### Quick Reference Commands

```bash
# Read specific doc when needed (examples)
cat docs/TROUBLESHOOTING.md        # Debugging issues
cat docs/AGENT_CATALOG.md          # Agent reference
cat docs/DATABASE_SCHEMA.md        # Schema reference
```

---

## Phase 6: Optional Memory (ON DEMAND)

Use AgentCore Memory resources ONLY if required by the task.

**Memory IDs (Provisioned in AWS):**

| Memory ID | Runtime | Purpose |
|-----------|---------|---------|
| `nexo_agent_mem-Z5uQr8CDGf` | agentcore-inventory | Smart Import episodic learning |
| `faiston_portal_agents_mem-*` | agentcore-portal | Portal/Academy STM conversation context |

> **Note:** Academy agents were consolidated into `agentcore-portal`. Check Terraform state for current memory IDs.

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
