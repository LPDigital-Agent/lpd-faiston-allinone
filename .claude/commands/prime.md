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
| **Phase**          | Phase 2 — SGA Module                     |

### Current Focus

SGA (Sistema de Gestão de Ativos) - Inventory Management with 14 AgentCore agents.
For requirements, see `docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md`.

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

### AgentCore Runtimes (100% A2A Architecture)

**SGA Module**: 14 dedicated AgentCore Runtimes (one per agent, A2A Protocol)

| Agent | Runtime ID | Purpose |
| ----- | ---------- | ------- |
| `nexo_import` | `faiston_sga_nexo_import` | Main orchestrator (ReAct pattern) |
| `learning` | `faiston_sga_learning` | Episodic memory & pattern learning |
| `validation` | `faiston_sga_validation` | Schema validation |
| `intake` | `faiston_sga_intake` | NF XML/PDF parsing |
| `estoque_control` | `faiston_sga_estoque_control` | Inventory operations |
| *+ 9 more* | `faiston_sga_{agent}` | See `docs/AGENT_CATALOG.md` |

**Communication**: JSON-RPC 2.0 over HTTP (A2A Protocol, port 9000)
**Memory**: AgentCore Memory (global namespace `/strategy/import/company`)
**Warm-Up**: EventBridge pings critical agents every 10 minutes

> **Key Docs:** `docs/AGENT_CATALOG.md` for full inventory, `docs/TROUBLESHOOTING.md` for HTTP 424.

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

## Phase 4.5: AgentCore Runtime Status (MANDATORY)

Use AgentCore CLI to check critical agent status:

```bash
echo "=== AGENTCORE RUNTIME STATUS ==="
echo "(CLI Reference: https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html)"
echo ""

# Check main orchestrator (nexo_import) status
cd server/agentcore-inventory/agents/nexo_import 2>/dev/null && agentcore status 2>&1 | head -15 || echo "AgentCore CLI not available or agent not configured"
cd - > /dev/null 2>&1 || true
```

**Key AgentCore CLI Commands:**
| Command | Purpose |
|---------|---------|
| `agentcore status` | Deployment state, memory config, endpoint readiness |
| `agentcore invoke` | Send JSON payload to test agent |
| `agentcore memory list` | List provisioned memory resources |
| `agentcore destroy` | Remove agent resources (use with caution)

---

## Phase 5: Architecture Snapshot (CONCEPTUAL)

```text
Frontend (Next.js 16 + React 19)
  └── AWS Cognito (NO Amplify)
        └── AWS Bedrock AgentCore Gateway
              └── 14 AgentCore Runtimes (SGA)
                    ├── A2A Protocol (JSON-RPC 2.0)
                    ├── AgentCore Memory (STM + LTM)
                    └── MCP Gateway Tools (PostgreSQL, S3, etc.)
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
| `docs/Faiston_Investory_Mamagement.md` | Strategic vision, As-Is/To-Be architecture |
| `docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md` | Current SGA patterns, hooks, agent flows |

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
| `nexo_sga_learning_memory-u3ypElEdl1` | agentcore-inventory | Smart Import episodic learning |
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

---

## Need Full Rules Reload?

If context drifts mid-session and you need ALL modular rules loaded without `/clear`:

```
/prime-all
```

This loads all 12 rule files from `.claude/rules/` into active context.
