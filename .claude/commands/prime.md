---
name: prime
description: Prime context with comprehensive Faiston NEXO project information
allowed-tools: Read, Bash, Glob, Grep, mcp__memory__read_graph, mcp__memory__search_nodes
---

# Faiston NEXO Context Prime

Load essential project context after `/clear` or new session start.

---

## Phase 1: Load Memory Context (MCP)

### Search Knowledge Graph for Project Context

```mcp
mcp__memory__search_nodes "Faiston NEXO"
```

```mcp
mcp__memory__search_nodes "project decisions architecture"
```

```mcp
mcp__memory__search_nodes "current tasks progress plans"
```

> **Note**: If memory is empty, continue with file-based context below.

---

## Phase 2: Load Project Instructions

### CLAUDE.md (CRITICAL - Must Read)

```bash
echo "Loading CLAUDE.md..."
cat CLAUDE.md
```

**Key Rules from CLAUDE.md**:
- **NEVER deploy from local console** - use ONLY GitHub Actions CI/CD
- **NEVER create AWS resources via CloudFormation/SAM** - use ONLY Terraform
- **ALWAYS use Terraform** for ALL AWS resources
- **Brand identity Faiston is MANDATORY** - see `docs faiston/manual_Faiston_FINAL.pdf`
- Branch prefix: `fabio/`
- Always create plans before implementation
- Use SubAgents for complex tasks

---

## 🚨 CRITICAL: Infrastructure Policy (MANDATORY)

### NEVER DO THIS:
1. **NEVER create AWS resources via CloudFormation/SAM** - use ONLY Terraform in `terraform/`
2. **NEVER create parallel environments** with different naming - consolidate FIRST
3. **NEVER hardcode AWS values** (account IDs, bucket names, domains) - use Terraform variables/locals
4. **NEVER deploy from local console** - use ONLY GitHub Actions CI/CD

### ALWAYS DO THIS:
1. **ALWAYS check existing resources BEFORE creating**:
   ```bash
   aws s3 ls | grep faiston                    # Check S3 buckets
   aws lambda list-functions | grep faiston    # Check Lambda functions
   aws cloudformation list-stacks              # Check for orphan stacks
   ```
2. **ALWAYS use Terraform** for ALL AWS resources
3. **ALWAYS run `terraform plan` before `terraform apply`** via GitHub Actions

### Resource Naming Convention:
| Resource | Pattern | Example |
|----------|---------|---------|
| S3 Bucket | `faiston-nexo-{purpose}-{env}` | `faiston-nexo-frontend-prod` |
| Lambda | `faiston-nexo-{function}` | `faiston-nexo-api` |
| DynamoDB | `faiston-nexo-{feature}-{env}` | `faiston-nexo-users-prod` |
| SSM Parameter | `/faiston-nexo/{param}` | `/faiston-nexo/ms-graph-secret` |
| AgentCore Runtime | `faiston_nexo_agents` | `faiston_nexo_agents` |

---

## Phase 3: Repository State

### Git Status

```bash
echo "Git Status"
echo "==========="
echo ""
echo "Branch: $(git branch --show-current)"
echo ""
echo "Status:"
git status --short
echo ""
echo "Recent Commits (5):"
git log --oneline -5
```

### Project Structure

```bash
echo "Project Structure"
tree -L 2 -I 'node_modules|dist|.git|.next' . 2>/dev/null | head -50
```

---

## Phase 4: Load Documentation

### PRD (Product Requirements Document)

```bash
echo "Loading PRD..."
cat product-development/current-feature/PRD.md 2>/dev/null | head -150
```

### Brand Guidelines Reference

```bash
echo "Brand Assets Available:"
ls -la "docs faiston/"
```

---

## Phase 5: Project Overview

### Project Identity

**Project**: Faiston NEXO
**Type**: AI-First All-in-One Intranet Portal
**Phase**: Phase 1 (Foundation)
**AI Assistant**: NEXO - Central orchestrator for all platform interactions

### Tech Stack

| Category | Technology |
|----------|------------|
| Frontend | Next.js 15 (App Router) + TypeScript |
| Styling | Tailwind CSS 4.0 + shadcn/ui |
| State | TanStack Query + Zustand |
| Animations | Framer Motion + Rive |
| Backend | Python 3.12 + AWS Lambda |
| AI Framework | Google ADK v1.0 |
| AI Runtime | AWS Bedrock AgentCore |
| Agent Protocol | A2A (Agent-to-Agent) |
| Auth | Amazon Cognito + Microsoft Entra (SSO) |
| Infrastructure | Terraform + GitHub Actions |

### Architecture Overview

```
Frontend (Next.js 15 - CloudFront + S3)
    │
    ├── AWS Cognito + Microsoft Entra (Authentication)
    │       └── OAuth 2.0 with Microsoft 365
    │       └── JWT tokens for AgentCore auth
    │
    └── AWS Bedrock AgentCore (faiston_nexo_agents)
            │
            ├── AgentCore Runtime
            │   └── NEXO Orchestrator Agent (Google ADK + Claude 4)
            │       ├── NewsAgent (RSS/API aggregation)
            │       ├── CalendarAgent (Microsoft Graph - Outlook)
            │       └── TeamsAgent (Microsoft Graph - Teams)
            │
            ├── AgentCore Memory (session + long-term)
            │
            └── AgentCore Gateway (MCP Servers)
                ├── Microsoft Graph MCP
                ├── News RSS MCP
                └── Internal APIs MCP
```

### Brand Identity (MANDATORY)

**Colors:**
```css
/* Background */
--faiston-bg-primary: #151720;    /* Dark theme (official) */

/* Blue Gradient */
--faiston-blue-dark: #2226C0;
--faiston-blue-mid: #0054EC;
--faiston-blue-light: #00FAFB;    /* Cyan */

/* Magenta Gradient */
--faiston-magenta-dark: #960A9C;
--faiston-magenta-mid: #FD11A4;
--faiston-magenta-light: #FD5665; /* Coral */
```

**Typography:**
- Logo: `Cocogoose Pro`
- Headings: `Roboto Slab Bold` (26pt)
- Subheadings: `Roboto Slab Regular` (20pt)
- Body: `Roboto Light` (16pt)

**Logo Files:**
- Dark background: `Logotipo_Faiston_branco.png`
- Light background: `Logotipo_Faiston_preto.png`
- Colored (dark bg): `Logotipo_Faiston_negativo.png`
- Colored (light bg): `Logotipo_Faiston_positivo.png`

### Directory Structure (Planned)

```
lpd-faiston-allinone/
├── .claude/                 # Claude Code configuration
│   ├── commands/           # Slash commands (/commit, /prime, etc.)
│   └── skills/             # Specialist skills
├── docs faiston/           # Brand assets and guidelines
├── product-development/    # PRD, feature docs, JTBD
│   ├── current-feature/    # Active feature documentation
│   └── resources/          # Templates and product overview
├── client/                 # Next.js 15 frontend (App Router)
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   │   ├── ui/           # shadcn/ui library
│   │   ├── dashboard/    # Bento Grid dashboard
│   │   ├── nexo/         # NEXO AI assistant UI
│   │   └── widgets/      # Calendar, Teams, News widgets
│   ├── lib/              # Utilities
│   └── services/         # API clients (agentcore.ts, ms-graph.ts)
├── server/                 # Python backend
│   └── agentcore/         # AgentCore Runtime
│       ├── main.py        # BedrockAgentCoreApp entrypoint
│       ├── agents/        # Google ADK Agents
│       │   ├── nexo_orchestrator.py
│       │   ├── news_agent.py
│       │   ├── calendar_agent.py
│       │   └── teams_agent.py
│       └── tools/         # Agent tools
└── terraform/             # AWS Infrastructure as Code
    ├── backend/          # Terraform state
    └── main/             # All AWS resources
```

---

## Phase 6: Phase 1 Features (Current Scope)

### Core Features to Build

| Feature | Description | Priority |
|---------|-------------|----------|
| **NEXO AI Assistant** | Central AI assistant interface | P0 |
| **Dashboard (Bento Grid)** | Modular widget layout | P0 |
| **Command Palette** | Cmd+K universal search/actions | P0 |
| **Tech News Feed** | Cloud/AI news aggregation | P1 |
| **Outlook Calendar Widget** | Microsoft Graph integration | P1 |
| **Teams Messages Widget** | Microsoft Graph integration | P1 |

### UI Design Principles

- **Optimistic UI**: Update before server confirmation
- **Bento Grid Layout**: Modular, responsive dashboard
- **Glassmorphism**: Modern dark mode with blur effects
- **Command Palette**: Keyboard-first navigation (Cmd+K)
- **Ghost Borders**: Subtle hover affordances
- **60fps Animations**: Framer Motion + Rive

---

## Phase 7: Available Skills

Use these skills for specialized tasks:

| Skill | Use For |
|-------|---------|
| `adk-agentcore-architect` | Google ADK agents, AWS Bedrock AgentCore, A2A protocol |
| `ui-ux-designer` | Component design, Tailwind CSS, glassmorphism, accessibility |
| `frontend-builder` | Next.js, React, TypeScript components |
| `backend-architect` | Python FastAPI, Lambda, DynamoDB |
| `ai-engineer` | LLM integration, prompt engineering, agent design |
| `code-review` | Code quality, security, performance review |

---

## Context Prime Complete

You now have:
- **Memory** - MCP knowledge graph searched
- **CLAUDE.md** - Project rules loaded
- **Git State** - Branch, status, recent commits
- **PRD** - Product requirements and specifications
- **Brand Identity** - Faiston colors, typography, logos
- **Architecture** - Tech stack and system design

**Project**: Faiston NEXO
**Type**: AI-First All-in-One Intranet Portal
**Stack**: Next.js 15 + Python 3.12 + Google ADK + AWS Bedrock AgentCore
**Phase**: Phase 1 (Foundation)

---

## Ready to Develop!

**Next Steps**:
1. Review any MCP memory results above
2. Check git status for uncommitted work
3. Review PRD at `product-development/current-feature/PRD.md`
4. Create plan before starting new work (TodoWrite tool)
5. Use SubAgents for complex tasks

**Git Workflow**:
- Branch prefix: `fabio/`
- Commit command: `/commit`
- Always plan before implementation

**Important Notes**:
- **CI/CD**: All deployments via GitHub Actions (NEVER deploy from local console)
- **Brand**: Follow Faiston brand guidelines strictly
- **AI-First**: Every feature should leverage NEXO AI assistant
