# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Memory Architecture**: This file contains ONLY essential instructions.
> Context-specific documentation is in subdirectory CLAUDE.md files (lazy-loaded).

---

## Primary Instructions
- NEVER create files on root unless necessary
- ALL documentation in `docs/` folder
- Be extremely concise in commits and interactions
- Always create plans before implementation

## GitHub & Git
- Primary method: GitHub CLI
- Branch prefix: `fabio/`

## SubAgents and Skills
- ALWAYS use cluade code SubAgents and Skills for parallel execution
- Use `prompt-engineer` SubAgent to improve prompts

---
## Authentication Policy
- **NO AWS Amplify** - EVER
- **Cognito**: PRIMARY authentication method (direct API, no SDK)

---

## Infrastructure Policy (MANDATORY)

### NEVER DO:
1. Create AWS resources via CloudFormation/SAM - use ONLY Terraform
2. Create parallel environments (prod vs prod-v2) - consolidate FIRST
3. Duplicate CORS - lives ONLY in `terraform/main/locals.tf`
4. Hardcode AWS values - use Terraform variables/locals
5. Deploy from local console - use ONLY GitHub Actions CI/CD

### ALWAYS DO:
1. Check existing resources BEFORE creating:
   ```bash
   aws s3 ls | grep hive
   aws lambda list-functions | grep hive
   aws cloudformation list-stacks
   ```
2. Use Terraform for ALL AWS resources
3. Update `terraform/main/locals.tf` for CORS changes
4. Run `terraform plan` via GitHub Actions before apply
---

## Project Overview

**Faiston NEXO** - AI-First All-in-One Intranet Portal for Faiston employees. The platform is commanded by the AI assistant **NEXO** which orchestrates all interactions, integrations, and automations.

**Status**: Phase 1 (Foundation) - Building core infrastructure and UI/UX

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS 4.0, shadcn/ui |
| Backend | Python 3.12+, Google ADK v1.0, AWS Lambda |
| AI Runtime | AWS Bedrock AgentCore (Runtime + Memory + Gateway) |
| Agent Protocol | A2A (Agent-to-Agent) for multi-agent orchestration |
| Infrastructure | AWS (Terraform only), GitHub Actions CI/CD |
| Auth | Amazon Cognito + Microsoft Entra (SSO) |

## Critical Rules

### Infrastructure (MANDATORY)

1. **NEVER deploy from local console** - use ONLY GitHub Actions CI/CD
2. **NEVER create AWS resources via CloudFormation/SAM** - use ONLY Terraform
3. **ALWAYS use Terraform** for ALL AWS resources
4. **ALWAYS run `terraform plan` before `terraform apply`** via GitHub Actions

### Brand Identity (MANDATORY)

The Faiston brand guidelines in `docs faiston/manual_Faiston_FINAL.pdf` must be followed strictly:

```css
/* Primary Colors */
--faiston-bg-primary: #151720;     /* Dark background (official) */
--faiston-blue-dark: #2226C0;      /* Blue gradient start */
--faiston-blue-light: #00FAFB;     /* Cyan */
--faiston-magenta-dark: #960A9C;   /* Magenta gradient start */
--faiston-magenta-light: #FD5665;  /* Coral */

/* Typography */
--font-display: 'Cocogoose Pro';   /* Logo/brand only */
--font-heading: 'Roboto Slab';     /* Titles */
--font-body: 'Roboto Light';       /* Body text */
```

Logo files: `docs faiston/Logotipo_Faiston_*.png`

## Project Structure

```
lpd-faiston-allinone/
├── .claude/                 # Claude Code configuration
│   ├── commands/           # Slash commands (/commit, /prime, etc.)
│   └── skills/             # Specialist skills (adk-agentcore-architect, ui-ux-designer, etc.)
├── docs faiston/           # Brand assets and guidelines
├── product-development/    # PRD, feature docs, JTBD
│   ├── current-feature/    # Active feature documentation
│   │   ├── PRD.md         # Product Requirements Document
│   │   ├── feature.md     # Feature specification
│   │   └── JTBD.md        # Jobs to Be Done analysis
│   └── resources/         # Templates and product overview
├── client/                 # Next.js frontend (to be created)
├── server/                 # Python backend + AgentCore agents (to be created)
└── terraform/              # AWS infrastructure (to be created)
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/prime` | Load project context (adapted from Hive Academy) |
| `/commit` | Create well-formatted commits |
| `/create-prd` | Create Product Requirements Document |
| `/ultra-think` | Deep analysis and problem solving |

## Available Skills

Use these skills for specialized tasks:

- **adk-agentcore-architect**: Google ADK agents, AWS Bedrock AgentCore, A2A protocol
- **ui-ux-designer**: Component design, Tailwind CSS, glassmorphism, accessibility
- **frontend-builder**: Next.js, React, TypeScript components
- **backend-architect**: Python FastAPI, Lambda, DynamoDB
- **ai-engineer**: LLM integration, prompt engineering, agent design

## Architecture Reference

```
Frontend (Next.js 15 - CloudFront + S3)
    │
    ├── AWS Cognito + Microsoft Entra (Authentication)
    │
    └── AWS Bedrock AgentCore
            │
            ├── AgentCore Runtime
            │   └── NEXO Orchestrator Agent (Google ADK)
            │       ├── NewsAgent (RSS/API aggregation)
            │       ├── CalendarAgent (Microsoft Graph)
            │       └── TeamsAgent (Microsoft Graph)
            │
            ├── AgentCore Memory (session + long-term)
            │
            └── AgentCore Gateway (MCP Servers)
                ├── Microsoft Graph MCP
                ├── News RSS MCP
                └── Internal APIs MCP
```

## Development Notes

- **UI Design**: Follow state-of-the-art 2025 patterns (Bento Grid, Glassmorphism, Optimistic UI, Command Palette)
- **AI-First**: Every feature should leverage NEXO AI assistant
- **Office 365 Integration**: Teams messages + Outlook Calendar via Microsoft Graph API
- **News Aggregation**: Tech news (Cloud, AI) from Brazil and international sources

## Key Documentation

- **PRD**: `product-development/current-feature/PRD.md` - Complete product requirements
- **Brand Guide**: `docs faiston/manual_Faiston_FINAL.pdf` - Visual identity rules
- **AgentCore Guide**: `.claude/skills/adk-agentcore-architect/IMPLEMENTATION_GUIDE.md`

### 🚨 Cold Start Limit (30 seconds) - CRITICAL
AgentCore has a **30-second cold start limit**. Exceeding this causes HTTP 424 errors and breaks ALL AI features.

**NEVER DO:**
1. Add heavy dependencies to `requirements.txt` (trafilatura, beautifulsoup4, lxml, Pillow, etc.)
2. Add imports to `agents/__init__.py` or `tools/__init__.py` - **MUST remain EMPTY**
3. Import agents at module level - each Google ADK import takes ~5-6 seconds

**ALWAYS DO:**
1. Keep `requirements.txt` minimal (currently: google-adk, google-genai, bedrock-agentcore, elevenlabs)
2. Use lazy imports in `main.py` - import agent only inside its handler function
3. Check AWS AgentCore pre-installed packages before adding new dependencies

---

---

## Important Notes (Do not Delete)

- All docs in `docs/` folder (not root)
- Only essential files in root: package.json, configs, CLAUDE.md, README.md
- All deployments via GitHub Actions (NEVER local console)
- TypeScript strict mode: DISABLED (rapid prototyping)
- Antes de criar, atualizar or fazer qualquer analise de agentes usando o AgentCore deve consultar o documento @docs/AgentCore/IMPLEMENTATION_GUIDE.md
- BE CAREFUL with the brazilian portuguese language when you write on the UI or text, do not forget the accent mark in the words also in the scripts to create voices end videos
- MUST USE Claude Skills avilable in all tasks.
- ATTENTION AND MANDATORY A documentação oficial da AWS mostra que o AgentCore Runtime já tem dezenas de bibliotecas pré-instaladas, antes de colocar bibliotecas adicionais no pacote de deploy dos agentes validar se estas já não são providas pela AWS no AgentCore Runtime.
- MUST USE MCP Context7 to check documentations a make sure you are using the best practices to build that functions or Code
- USE All Best practices for the SDLC (Software Developer Life Cicle) includes comments in all code e principios de Clean Code.
- MUST MANDATORY when create any Terraform check the MCP Terraform to make sure you are using the best practices to create terraform IaC and the last version of the modules.
- MUST Check the /docs/Claude Code/ and read the documentations about best practices in how to create prompts and working better with claude code and apply in all you are doing with claude code to make it better to build softwares and solutions.