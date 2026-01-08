---
name: prime
description: Prime context with comprehensive Faiston NEXO project information
allowed-tools: Read, Bash, Glob, Grep, mcp__memory__read_graph, mcp__memory__search_nodes
---

# Faiston NEXO Context Prime

Load essential project context after `/clear` or new session start.

---

## Phase 1: Load Project Instructions

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
| DynamoDB | `faiston-one-sga-{feature}-{env}` | `faiston-one-sga-inventory-prod` |
| SSM Parameter | `/faiston-nexo/{param}` | `/faiston-nexo/ms-graph-secret` |
| AgentCore Academy | `faiston_academy_agents` | `faiston_academy_agents-ODNvP6HxCD` |
| AgentCore Inventory | `faiston_asset_management` | `faiston_asset_management-uSuLPsFQNH` |
| AgentCore Portal | `faiston_portal_agents` | `faiston_portal_agents-*` |
| CloudFront Function | `faiston-one-{name}` | `faiston-one-url-rewriter` |

### AWS Profile (Local Development)
```bash
# Profile: faiston-aio (account 377311924364)
aws sts get-caller-identity --profile faiston-aio
```

### Terraform State Management
- **State bucket**: `faiston-terraform-state` (us-east-2, versioned, encrypted)
- **Lock table**: `faiston-terraform-locks` (DynamoDB)
- **State path**: `faiston-one/terraform.tfstate`
- **Resources managed**: 74+ AWS resources

### GitHub Actions Workflows
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `terraform.yml` | Push to `terraform/**` | Plan on PR, Apply on merge |
| `deploy-frontend.yml` | Push to `client/**` | Build & deploy to S3/CloudFront |
| `deploy-agentcore-academy.yml` | Push/Manual | Deploy Academy agents (JWT Auth via secrets + boto3 control client) |
| `deploy-agentcore-inventory.yml` | Push/Manual | Deploy SGA agents (JWT Auth via secrets + boto3 control client) |
| `deploy-agentcore-portal.yml` | Push/Manual | Deploy Portal NEXO agents (JWT Auth via secrets + boto3 control client) |
| `deploy-sga-postgres-lambda.yml` | Push/Manual | Deploy PostgreSQL MCP tools Lambda |
| `migrate-sga-schema.yml` | Manual | Apply PostgreSQL schema via Lambda bridge |

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
| Backend | Python 3.13 + AWS Lambda (arm64) |
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

### Directory Structure (Current)

```
lpd-faiston-allinone/
├── .claude/                 # Claude Code configuration
│   ├── commands/           # Slash commands (/commit, /prime, etc.)
│   └── skills/             # Specialist skills
├── docs faiston/           # Brand assets and guidelines
├── product-development/    # PRD, feature docs, JTBD
├── client/                 # Next.js 15 frontend (App Router)
│   ├── app/               # App Router pages (55+ routes)
│   ├── components/        # React components
│   │   ├── ui/           # shadcn/ui library (15+ components)
│   │   └── ferramentas/  # Ferramentas modules
│   │       ├── academy/  # Faiston Academy
│   │       │   ├── classroom/  # 14 floating panels
│   │       │   └── dashboard/  # 5 dashboard components
│   │       └── ativos/   # Asset Management (SGA 2.0)
│   │           └── estoque/    # Inventory management
│   │               ├── mobile/  # 3 PWA components
│   │               └── nexo/    # 4 NEXO AI components
│   ├── contexts/          # React contexts
│   │   ├── Academy*       # 3 Academy contexts
│   │   └── ativos/        # 6 SGA contexts
│   ├── hooks/             # Custom hooks
│   │   ├── academy/      # 12 Academy-specific hooks
│   │   └── ativos/       # 17 SGA-specific hooks
│   ├── lib/               # Utilities
│   │   ├── academy/      # Academy types, constants
│   │   └── ativos/       # SGA types, constants
│   └── services/          # API clients
│       ├── agentcoreBase.ts     # Factory base (unified retry/session/SSE)
│       ├── academyAgentcore.ts  # Academy AgentCore (uses base)
│       ├── sgaAgentcore.ts      # SGA AgentCore (uses base)
│       └── portalAgentcore.ts   # Portal AgentCore (uses base)
├── server/                 # Python backend
│   ├── agentcore-academy/ # Faiston Academy AgentCore (19 actions)
│   ├── agentcore-inventory/ # SGA Inventory AgentCore (30+ actions)
│   │   ├── agents/        # 10 Google ADK Agents
│   │   └── tools/         # dynamodb, s3, nf_parser, hil
│   └── agentcore-portal/  # Portal NEXO Orchestrator (news, A2A delegation)
├── terraform/             # AWS Infrastructure as Code
│   └── main/              # All AWS resources (28+ .tf files)
│       ├── main.tf        # S3 backend, providers
│       ├── cloudfront.tf  # CDN + URL rewriter function
│       ├── s3*.tf         # 6 S3 buckets (frontend, academy, sga)
│       ├── dynamodb*.tf   # 4 DynamoDB tables
│       ├── rds_aurora_sga.tf    # Aurora PostgreSQL cluster
│       ├── rds_proxy_sga.tf     # RDS Proxy (connection pooling)
│       ├── lambda_sga_*.tf      # PostgreSQL tools + schema migrator
│       ├── agentcore_gateway.tf # MCP Gateway + targets
│       └── iam*.tf        # IAM roles/policies
├── data/                   # Seed data
│   └── faiston_sga2_estoque_simulado_sap.csv  # SGA test data
└── docs/                   # Documentation
    ├── AgentCore/         # AgentCore implementation guide
    ├── agents/            # Agent documentation
    ├── architecture/      # Architecture docs
    └── Claude Code/       # Claude Code best practices
```

---

## Faiston Academy Module (Migrated from Hive Academy)

Educational platform at `/ferramentas/academy/` with AI-powered features.

### Academy Migration Progress
- ✅ Sprint 1: Terraform Infrastructure (Cognito, S3, DynamoDB, IAM)
- ✅ Sprint 2: Backend AgentCore (19 actions, NEXO agent, tools)
- ✅ Sprint 3: Frontend Foundation (services, contexts, hooks)
- ✅ Sprint 4: Frontend Components (14 classroom + 5 dashboard) + TypeScript Fixes
- ⏳ Sprint 5: Frontend Pages (routes)
- ⏳ Sprint 6: Style and Polish

### Sprint 4 Build Fixes (January 2026)
New components added: `textarea.tsx`, `slider.tsx`, `markdown-content.tsx`, `use-toast.ts`, `skeleton.tsx`
New hooks: `useLibrary.ts`
New types: `types/zoom-videosdk.d.ts`
**Pattern**: All Academy hooks use object-based parameters (not positional)
**TypeScript Fixes**: Discriminated union types in `portalAgentcore.ts` for `DailySummarySectionData`
**Service Factory (January 2026)**: Created `agentcoreBase.ts` - unified retry/session/SSE across all 3 services (~450 lines deduped)
**SigV4 Fix (January 2026)**: All 3 AgentCore deploy workflows use boto3 client instead of raw SigV4 signing for JWT Authorizer configuration

### Key Adaptations (Hive → Faiston)
- "Sasha" → "NEXO" (AI tutor)
- Colors: cyan/purple → `var(--faiston-magenta-mid)` / `var(--faiston-blue-mid)`
- Storage: `hive_` → `faiston_academy_`
- Router: react-router-dom → Next.js App Router

---

## SGA Inventory Module (Gestao de Estoque)

Asset management system at `/ferramentas/ativos/estoque/`. Complete product implementation.

### SGA Implementation Progress (January 2026)
- ✅ Sprint 1-3: Backend (Terraform + 10 AgentCore agents)
- ✅ Sprint 4: Frontend Foundation (6 contexts, 12 hooks, services)
- ✅ Sprint 5-6: Frontend Pages (25+ pages, movement forms)
- ✅ Sprint 7-8: NEXO Copilot + Mobile/PWA components
- ✅ Audit: ADK/AgentCore compliance (95% - lxml fixed)
- ✅ SGA 2.0 Phases 1-3: Expedição, Cotação, Reversa, Analytics, Reconciliação SAP
- ✅ Wiki: 14 sections documenting all SGA features
- ✅ Unified Entry: Multi-source tabs (NF, Image OCR, SAP Export, Manual)
- ✅ **Estoque Page Refactor (January 2026)**: Unified navigation into single ModuleNavigation (8 items), removed KPIs (already in Dashboard)
- ✅ **Smart Import**: Universal file importer - auto-detects XML/PDF/CSV/XLSX/JPG/PNG/TXT
- ✅ **NEXO Intelligent Import (January 2026)**: TRUE Agentic AI-First import with ReAct pattern (OBSERVE → THINK → ASK → LEARN → ACT)
- ✅ **NEXO Stateless Architecture (January 2026)**: Frontend-stateful + backend-stateless pattern (session_state passed in each API call)
- ✅ **PostgreSQL Migration (January 2026)**: Complete Aurora PostgreSQL infrastructure
  - Aurora Serverless v2 cluster with RDS Proxy (connection pooling)
  - 13 tables, 110 indexes, 8 materialized views
  - VPC with private subnets + S3/Secrets Manager/RDS endpoints
  - MCP Gateway + Lambda MCP tools (8 tools working)
  - Schema migration workflow via Lambda bridge (GitHub Actions)
- ✅ **Schema-Aware Import (January 2026)**: Agents OBSERVE PostgreSQL schema before analyzing files
  - Dynamic column matching replaces 50+ hardcoded patterns
  - Gemini prompts include target table schema + ENUM values
  - Pre-execution validation prevents invalid mappings
  - Learned mappings tracked by schema_version
- ⏳ Phase 4: SAP API Integration (pending credentials)

### SGA Key Components
| Category | Components |
|----------|------------|
| **Backend Agents (11)** | estoque_control, intake, reconciliacao, compliance, comunicacao, expedition, carrier, reverse, import, **nexo_import** (stateless), base |
| **Backend Tools (9)** | dynamodb_client, s3_client, nf_parser, hil_workflow, sheet_analyzer, postgres_client, **schema_provider**, **schema_column_matcher**, **schema_validator** |
| **Contexts** | AssetManagement, InventoryOperations, InventoryCount, NexoEstoque, TaskInbox, OfflineSync |
| **Hooks (17)** | useAssets, useMovements, useLocations, usePartNumbers, useNFReader, useSerialScanner, useImageOCR, useSAPImport, useManualEntry, useBulkImport, useSmartImporter, **useSmartImportNexo** |
| **NEXO AI** | NexoCopilot, NexoSearchBar, UnifiedSearch, **SmartImportNexoPanel** |
| **Mobile/PWA** | MobileScanner, MobileChecklist, ConfirmationButton |
| **Smart Import** | SmartUploadZone, SmartPreview, NFPreview, SpreadsheetPreview, TextPreview, PendingEntriesList |

### SGA Pages Structure (25+ pages)
```
/ferramentas/ativos/estoque/
├── page.tsx           # Operations hub + unified ModuleNavigation (8 items)
├── [id]/              # Asset detail
├── lista/             # Asset list
├── cadastros/         # Part numbers, locations, projects
├── movimentacoes/     # Entrada, saida, transferencia, reserva, ajuste, importar
├── inventario/        # Campaigns, counting, novo
├── expedicao/         # AI-guided expedition + cotacao
├── reversa/           # Reverse logistics
├── analytics/         # Accuracy KPI dashboard
├── reconciliacao/sap/ # SAP comparison
└── wiki/              # User guide (14 sections)
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
**Stack**: Next.js 15 + Python 3.13 + Google ADK + AWS Bedrock AgentCore
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
