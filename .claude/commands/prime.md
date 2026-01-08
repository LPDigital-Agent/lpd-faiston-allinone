---
name: prime
description: Prime Claude Code context (rules + product + code) after /clear
allowed-tools: Read, Bash, Glob, Grep, mcp__memory__read_graph, mcp__memory__search_nodes
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
Rules are NOT duplicated here.
CLAUDE.md is the only source of truth for architecture, infra, security, and AI policies.

Phase 2: Product Context (MANDATORY)
Product Definition
Product: Faiston NEXO

Type: AI-First, 100% Agentic Intranet Platform

AI Orchestrator: NEXO

Phase: Phase 1 — Foundation

Load PRD (Preview Only)
bash
Copy code
cat product-development/current-feature/PRD.md | head -120
If deeper requirements are needed, open the PRD fully on demand.

Phase 3: Codebase Orientation (MANDATORY)
High-Level Repository Map (NO DUMPS)
bash
Copy code
ls -la
Key areas:

client/ → Next.js frontend

server/ → Google ADK + Bedrock AgentCore agents

terraform/ → ALL AWS infrastructure (Terraform only)

docs/ → Documentation

.claude/ → Claude Code commands and skills

Minimal Tree (2 levels max)
bash
Copy code
tree -L 2 -I 'node_modules|dist|.git|.next' . | head -40
Phase 4: Current Work Context (MANDATORY)
bash
Copy code
git branch --show-current
git status --short
git log --oneline -5
This defines what is currently in progress.

Phase 5: Architecture Snapshot (CONCEPTUAL)
text
Copy code
Frontend (Next.js 15)
  └── AWS Cognito + Microsoft Entra
        └── AWS Bedrock AgentCore
              ├── Runtime (Google ADK agents)
              ├── Memory (STM + LTM)
              └── Gateway (MCP tools)
Detailed diagrams live in docs/architecture/.

Phase 6: Optional Memory (ON DEMAND)
Use MCP memory ONLY if required by the task:

mcp__memory__search_nodes

mcp__memory__read_graph

Do NOT preload memory unnecessarily.

Phase 7: Prime Complete (MANDATORY NEXT STEP)
Before writing any code:

Restate the key constraints from CLAUDE.md

State what you are about to build or change

Create a PLAN

Only then implement

PRIME AUDIT RULE (MANDATORY)
/prime MUST stay lightweight.

NOT allowed here:

Large file lists

Sprint logs

Changelogs

Component inventories

Full architecture documents

If more detail is needed → open the specific document or module CLAUDE.md.