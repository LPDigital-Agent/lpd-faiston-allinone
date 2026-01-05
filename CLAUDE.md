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

## AWS Configuration

- **MANDATORY** to Deploy for Developer:
  - AWS Account ID: 377311924364\
  - AWS Regionb: us-east-2 
  
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
│   └── resources/         # Templates and product overview
├── client/                 # Next.js 15 frontend (App Router)
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   │   ├── ui/           # shadcn/ui library (15+ components)
│   │   └── ferramentas/  # Ferramentas modules
│   │       ├── academy/  # Faiston Academy (migrated from Hive Academy)
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
│       ├── academyAgentcore.ts  # Academy AgentCore
│       └── sgaAgentcore.ts      # SGA AgentCore
├── server/                 # Python backend
│   ├── agentcore-academy/ # Faiston Academy AgentCore agents
│   │   ├── main.py        # BedrockAgentCoreApp entrypoint (19 actions)
│   │   ├── agents/        # Google ADK Agents (NEXO, flashcards, etc.)
│   │   └── tools/         # Agent tools (elevenlabs, heygen, youtube)
│   └── agentcore-inventory/ # SGA Inventory AgentCore agents
│       ├── main.py        # BedrockAgentCoreApp entrypoint (30+ actions)
│       ├── agents/        # 5 Google ADK Agents
│       └── tools/         # 4 tools (dynamodb, s3, nf_parser, hil)
└── terraform/             # AWS Infrastructure as Code
    └── main/              # All AWS resources
        ├── Cognito, CloudFront, IAM
        ├── DynamoDB (academy + 3 SGA tables)
        └── S3 (6 buckets: academy + sga)
```

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `terraform.yml` | Push to `terraform/**` or manual | Plan on PR, Apply on merge to main |
| `deploy-frontend.yml` | Push to `client/**` | Build Next.js and sync to S3 + CloudFront |
| `deploy-agentcore-academy.yml` | Manual dispatch | Deploy Academy agents to Bedrock AgentCore |
| `deploy-agentcore-inventory.yml` | Manual dispatch | Deploy SGA Inventory agents to Bedrock AgentCore |

## Available Commands

| Command | Description |
|---------|-------------|
| `/prime` | Load project context (adapted from Hive Academy) |
| `/commit` | Create well-formatted commits |
| `/create-prd` | Create Product Requirements Document |
| `/ultra-think` | Deep analysis and problem solving |
| `/sync-project` | Synchronize all project documentation |

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

---

## DO NOT REMOVE
###Important (Never Change or replace it)
### Important (Never Change or replace it)

- MUST MANDATORY use ONLY **Gemini 3.0 Family** models (**Pro or Flash**).
- USING ANY OTHER MODEL, VERSION, OR FAMILY IS **STRICTLY FORBIDDEN**.

- MUST MUST MANDATORY use **Agent Architecture** for **ALL microservices**, **WHEN IT MAKES SENSE**.
  - “MAKES SENSE” means the service involves **reasoning, orchestration, decision-making, autonomy, learning, memory, workflows, or multi-step execution**.

- If it DOES NOT MAKE SENSE:
  - you MUST still design the service using **Agentic AI Architecture** based on **Google ADK, A2A, MCP, A2P, and Memory**.
  - In this case, you MUST **STOP** and **ASK ME** to **VALIDATE AND APPROVE** the architectural decision **BEFORE IMPLEMENTING ANY CODE**.

- ONLY IF I explicitly approve NOT using Agentic Architecture:
  - you MUST then implement the service using **microservices**, **serverless**, and **event-driven architecture**.

- ANY ASSUMPTION ABOUT ARCHITECTURE **WITHOUT MY EXPLICIT APPROVAL** IS **NOT ALLOWED**.

- MUST MANDATORY use the **A2A Python SDK** located at:  
  https://github.com/a2aproject/a2a-python

- MUST MANDATORY use the **Google ADK Framework**, strictly following **OFFICIAL DOCUMENTATION**, including but not limited to:
  - https://google.github.io/adk-docs/
  - https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/
  - https://docs.cloud.google.com/agent-builder/agent-development-kit/overview
  - https://cloud.google.com/blog/topics/developers-practitioners/build-your-first-adk-agent-workforce
  - https://github.com/google/adk-python

- MUST ONLY use **GEMINI 3 FAMILY MODELS**, as defined in **Google Official Documentation**:
  - https://ai.google.dev/gemini-api/docs/models
  - https://ai.google.dev/gemini-api/docs/gemini-3

- USING OLDER GEMINI VERSIONS, EXPERIMENTAL MODELS, OR UNLISTED VARIANTS IS **NOT PERMITTED**.

#### HARD STOP & FAILURE CONDITIONS

- IF ANY RULE ABOVE CANNOT BE MET:
  - YOU MUST **STOP IMMEDIATELY**.
  - YOU MUST **EXPLAIN WHY**.
  - YOU MUST **ASK FOR EXPLICIT APPROVAL OR GUIDANCE** BEFORE CONTINUING.

- DO NOT AUTOFIX.
- DO NOT SUBSTITUTE TECHNOLOGIES.
- DO NOT SIMPLIFY THE ARCHITECTURE WITHOUT PERMISSION.

#### DEFAULT BEHAVIOR

- WHEN IN DOUBT → **ASK ME FIRST**.
- WHEN A CHOICE EXISTS → **PRESENT OPTIONS AND TRADE-OFFS**.
- WHEN A SHORTCUT EXISTS → **DO NOT TAKE IT WITHOUT APPROVAL**.

> **Memory Architecture**: This file contains ONLY essential instructions.
> Context-specific documentation is in subdirectory CLAUDE.md files (lazy-loaded).
- NEVER create files on root unless necessary
- ALL documentation in `docs/` folder
- Be extremely concise in commits and interactions
- Always create plans before implementation

---

## Key Documentation

- **PRD**  
  `product-development/current-feature/PRD.md`  
  Complete product requirements and scope.

- **Brand Guide**  
  `docs faiston/manual_Faiston_FINAL.pdf`  
  Visual identity rules (colors, typography, spacing, logo usage).

- **AgentCore Guide**  
  `.claude/skills/adk-agentcore-architect/IMPLEMENTATION_GUIDE.md`  
  AgentCore architecture + implementation rules.

---

## 🚨 Cold Start Limit (30 seconds) — CRITICAL

AgentCore has a **30-SECOND COLD START LIMIT**.  
Exceeding this causes **HTTP 424 errors** and **BREAKS ALL AI FEATURES**.

### ❌ NEVER DO

1. Add heavy dependencies to `requirements.txt`  
   Examples: `trafilatura`, `beautifulsoup4`, `lxml`, `Pillow`, or anything similar/heavy.
2. Add imports to `agents/__init__.py` or `tools/__init__.py`  
   These files **MUST remain EMPTY**.
3. Import agents at module level  
   Each Google ADK import may take ~**5–6 seconds** and will destroy cold start.

### ✅ ALWAYS DO

1. Keep `requirements.txt` minimal
   Current baseline: `google-adk`, `google-genai`, `bedrock-agentcore`, `elevenlabs`
2. Use **lazy imports** in `main.py`
   Import each agent **ONLY inside** its handler function.
3. Check AWS AgentCore pre-installed packages BEFORE adding any dependency
   Do not ship packages that already exist in the runtime.
4. Use Python stdlib for XML parsing (`xml.etree.ElementTree`)
   **NEVER use lxml** - it's a heavy C extension that violates cold start limits.

---

## Important Notes (DO NOT DELETE)

- All docs MUST stay in `docs/` folder (NOT root).
- Only essential files are allowed in root: `package.json`, configs, `CLAUDE.md`, `README.md`.
- ALL deployments via GitHub Actions — **NEVER local console**.
- TypeScript strict mode: **DISABLED** (rapid prototyping).

- Antes de criar, atualizar ou fazer qualquer análise de agentes usando o AgentCore,  
  MUST consultar o documento: `@docs/AgentCore/IMPLEMENTATION_GUIDE.md`.

- BE CAREFUL with Brazilian Portuguese in UI text and scripts (voices/videos).  
  Accent marks are MANDATORY (ex: “ação”, “técnico”, “integração”).

- MUST USE Claude Skills available in all tasks.

- ATTENTION AND MANDATORY:  
  A documentação oficial da AWS mostra que o AgentCore Runtime já tem dezenas de bibliotecas pré-instaladas.  
  Antes de adicionar qualquer dependência ao deploy package, VALIDAR se já não existe no runtime.

- MUST USE MCP Context7 to check documentation and ensure best practices before implementing any function or code.

- USE best practices for the SDLC (Software Development Life Cycle):  
  comments in all code + Clean Code principles.

- MUST MANDATORY when creating ANY Terraform:  
  check MCP Terraform to ensure best practices and latest stable modules/providers.

- MUST check `/docs/Claude Code/` and apply best practices for prompts and working with Claude Code in ALL tasks.

---
## Faiston Academy Module

Migrated from Hive Academy to `/ferramentas/academy/`. Educational platform with AI-powered learning features.

### Academy Components (Sprint 4 Complete)

**Classroom Panels (14):**
- `FloatingPanel` - Draggable/resizable container with macOS-style controls
- `PanelTitleBar` - Traffic light buttons (close/minimize/maximize)
- `ClassroomToolbar` - Panel toggle buttons
- `VideoPlayerPanel` - YouTube player with transcript sync
- `NexoAIPanel` - AI tutor chat (renamed from Sasha)
- `TranscriptionPanel` - Video transcript with timestamp navigation
- `FlashcardsPanel` - AI-generated study cards
- `MindMapPanel` - Hierarchical concept visualization
- `AudioClassPanel` - ElevenLabs TTS podcast-style lessons
- `SlideDeckPanel` - AI-generated slide presentations
- `LibraryPanel` - Materials + YouTube recommendations
- `NotesEditorPanel` - Auto-save notes with localStorage
- `ExtraClassPanel` - HeyGen personalized video lessons
- `ReflectionModal` - Learning reflection with AI feedback

**Dashboard Components (5):**
- `CourseCard` - Course thumbnail with progress
- `CourseCarousel` - Horizontal scrollable course list
- `CoachNexoCard` - AI coach recommendations
- `MetricCard` - Stat display with trend indicators
- `LearningMapSection` - Learning journey progress

### Academy Hooks (12)
`client/hooks/academy/`: useNexoAI, useFlashcards, useMindMap, useAudioClass, useSlideDeck, useReflection, useFloatingPanel, useExtraClass, useVideoClass, useYouTubeRecommendations, useLibrary, index

### Academy Services (2)
- `academyAgentcore.ts` - AgentCore Runtime invocation with JWT auth
- `academyCognito.ts` - Cognito token management

### Academy Contexts (3)
- `AcademyClassroomContext` - Panel state, current episode
- `AcademyTrainingContext` - NEXO Tutor custom trainings
- `AcademyZoomContext` - Live class with Zoom SDK

### Key Adaptations (Hive → Faiston)
- Renamed "Sasha" → "NEXO" throughout
- Colors: cyan/purple → `var(--faiston-magenta-mid)` / `var(--faiston-blue-mid)`
- Storage keys: `hive_` → `faiston_academy_`
- Router: react-router-dom → Next.js useRouter
- IDs: number → string (for Next.js params)

### Sprint 4 TypeScript Fixes (January 2026)
Components and utilities added to fix build errors:

**New shadcn/ui Components:**
- `client/components/ui/textarea.tsx` - Textarea form control
- `client/components/ui/slider.tsx` - Slider input control
- `client/components/ui/markdown-content.tsx` - Markdown rendering with react-markdown
- `client/components/ui/use-toast.ts` - Toast notification hook

**New Hooks:**
- `client/hooks/academy/useLibrary.ts` - Library file management

**New Type Declarations:**
- `client/types/zoom-videosdk.d.ts` - Zoom Video SDK types for dynamic import

**Hook API Pattern:**
All Academy hooks use **object-based parameters**:
```tsx
// CORRECT
useMindMap({ courseId, episodeId, episodeTitle, onSeek });

// WRONG (positional args)
useMindMap(courseId, episodeId, episodeTitle, onSeek);
```

**Type Re-exports:**
Hooks that import types must re-export them for consumers:
```tsx
// At end of hook file
export type { MindMapNode } from '@/lib/academy/types';
export { DECK_ARCHETYPES } from '@/lib/academy/constants';
```

---
## SGA Inventory Module (Gestao de Estoque)

Asset/Inventory management system at `/ferramentas/ativos/estoque/`. Full product (not MVP) with AI-powered features.

### SGA Implementation Progress (January 2026)
- ✅ Sprint 1: Terraform Infrastructure (DynamoDB x3, S3, IAM)
- ✅ Sprint 2: Backend Core Agents (EstoqueControl, Intake)
- ✅ Sprint 3: Backend Advanced Agents (Reconciliacao, Compliance, Comunicacao)
- ✅ Sprint 4: Frontend Foundation (contexts x6, hooks x12, services)
- ✅ Sprint 5: Frontend Pages (15+ pages: dashboard, cadastros, movimentacoes, inventario)
- ✅ Sprint 6: Movement Forms (entrada, saida, transferencia, reserva, ajuste)
- ✅ Sprint 7: NEXO Copilot (NexoCopilot, NexoSearchBar, UnifiedSearch)
- ✅ Sprint 8: Mobile/PWA (MobileScanner, MobileChecklist, ConfirmationButton)
- ✅ Audit: ADK/AgentCore compliance (95% - lxml fixed, memory strategies pending)
- ✅ SGA 2.0 Phase 1-3: Expedição Inteligente, Cotação de Frete, Reversa, Analytics, Reconciliação SAP
- ✅ Wiki User Guide: 14 sections documenting all SGA features
- ✅ UI Refinement: QuickActions redesigned to compact full-width layout
- ✅ Unified Entry: Multi-source material entry (NF-e, Image OCR, SAP Export, Manual)
- ✅ **Smart Import (January 2026)**: Universal file importer with auto-detect (XML/PDF/CSV/XLSX/JPG/PNG/TXT)
- ⏳ Phase 4: SAP API Integration (requires SAP credentials)

### SGA Backend Agents (10)
`server/agentcore-inventory/agents/`:
- `estoque_control_agent.py` - Core +/- movements
- `intake_agent.py` - NF-e PDF/XML/Image extraction (Gemini Vision OCR)
- `reconciliacao_agent.py` - Divergence detection
- `compliance_agent.py` - Policy validation
- `comunicacao_agent.py` - Notifications
- `expedition_agent.py` - AI-guided shipping with SAP format
- `carrier_agent.py` - Freight quotation and carrier comparison
- `reverse_agent.py` - Returns/reverse logistics management
- `import_agent.py` - CSV/Excel bulk import processing
- `base_agent.py` - Base agent class with common utilities

### SGA Contexts (6)
`client/contexts/ativos/`:
- `AssetManagementContext` - Global state, filters
- `InventoryOperationsContext` - Movement operations
- `InventoryCountContext` - Physical counting sessions
- `NexoEstoqueContext` - AI assistant state
- `TaskInboxContext` - HIL approval tasks
- `OfflineSyncContext` - PWA offline queue

### SGA Hooks (16)
`client/hooks/ativos/`:
- `useAssets`, `useAssetDetail` - Asset queries
- `useMovements`, `useMovementMutations`, `useMovementValidation` - Movement operations
- `useLocations`, `usePartNumbers`, `useProjects` - Master data
- `useBalanceQuery`, `useNFReader`, `useSerialScanner` - Utilities
- `useImageOCR` - Image OCR for scanned NF photos via Gemini Vision
- `useSAPImport` - SAP CSV/XLSX import with full asset creation
- `useManualEntry` - Manual entry without source document
- `useBulkImport` - Bulk CSV/Excel import processing
- `useSmartImporter` - **NEW** Universal auto-detect importer (XML/PDF/CSV/XLSX/JPG/PNG/TXT)

### SGA Frontend Pages (25+)
`client/app/(main)/ferramentas/ativos/estoque/`:
- `page.tsx` - Dashboard with KPIs, Quick Actions, and inbox
- `[id]/page.tsx` - Asset detail with timeline
- `lista/page.tsx` - Asset list with filters
- `cadastros/` - Part numbers, locations, projects (3 pages)
- `movimentacoes/` - Entrada, saida, transferencia, reserva, ajuste, importar (7 pages)
- `inventario/` - Campaigns, counting sessions, novo (3 pages)
- `expedicao/` - AI-guided expedition + cotacao (2 pages)
- `reversa/` - Reverse logistics management
- `analytics/` - Accuracy KPI dashboard
- `reconciliacao/sap/` - SAP comparison and divergence resolution
- `wiki/` - User guide with 14 sections (updated January 2026)

### SGA Components
**NEXO AI (4):** `NexoCopilot`, `NexoSearchBar`, `UnifiedSearch`, index
**Mobile/PWA (3):** `MobileScanner`, `MobileChecklist`, `ConfirmationButton`
**Smart Import (7):** `SmartUploadZone`, `SmartPreview`, `NFPreview`, `SpreadsheetPreview`, `TextPreview`, `PendingEntriesList`, index
**Legacy Tabs (4):** `EntradaNFTab`, `EntradaImagemTab`, `EntradaSAPTab`, `EntradaManualTab` (deprecated, kept for reference)

### SGA Terraform Resources
`terraform/main/`:
- `dynamodb_sga_inventory.tf` - Main inventory table (6 GSIs)
- `dynamodb_sga_hil.tf` - Human-in-the-Loop tasks
- `dynamodb_sga_audit.tf` - Audit log
- `s3_sga_documents.tf` - NF-e and evidence storage
- `iam_sga_agentcore.tf` - AgentCore IAM policies
- `cloudfront.tf` - CDN with URL rewriter function for Next.js static export

### Terraform State Management (January 2026)
Remote state is enabled with S3 backend and DynamoDB locking:
- **State bucket**: `faiston-terraform-state` (us-east-2, versioned, encrypted)
- **Lock table**: `faiston-terraform-locks` (DynamoDB)
- **State path**: `faiston-one/terraform.tfstate`
- **Resources imported**: 74 AWS resources (CloudFront, S3 x6, DynamoDB x4, IAM, SSM)

### CloudFront URL Rewriter (CRITICAL)
Next.js static export with `trailingSlash: true` requires a CloudFront Function to rewrite URLs.
S3 REST API (via OAC) doesn't support automatic `index.html` resolution.

**Function**: `faiston-one-url-rewriter` (viewer-request)
- `/path` → `/path/index.html`
- `/path/` → `/path/index.html`
- `/path.js` → unchanged (file extension)

Without this function, navigation to modules like `/ferramentas/ativos/dashboard` fails and shows root dashboard.

### Static Export Pattern (IMPORTANT)
For dynamic routes (`[id]`, `[slug]`) with `output: 'export'`:
```tsx
// page.tsx - Server Component
import { ClientComponent } from './ClientComponent';

export async function generateStaticParams(): Promise<{ id: string }[]> {
  return [{ id: '_' }];  // Placeholder for SPA fallback
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ClientComponent id={id} />;
}
```
```tsx
// ClientComponent.tsx - Client Component
'use client';
export function ClientComponent({ id }: { id: string }) {
  // All client-side logic here
}
```

---

## Known Issues & Fixes (January 2026)

### 1. S3 Bucket Tags - No Commas Allowed
**Issue**: AWS S3 bucket tags reject values containing commas
**Fix**: Use hyphens instead of commas in tag values
```hcl
# WRONG
Purpose = "NF-e files, evidence photos, and documents"

# CORRECT
Purpose = "NF-e files - evidence photos - documents"
```

### 2. CloudFront Function Naming After Import
**Issue**: When importing existing CloudFront Functions to Terraform, name mismatch causes destroy/recreate cycle that fails (function in use)
**Fix**: Use explicit hardcoded name matching AWS resource, not pattern-based names
```hcl
# After import, use exact AWS name
name = "faiston-one-url-rewriter"  # NOT ${local.name_prefix}-url-rewriter
```

### 3. Terraform State Lock Cleanup
**Issue**: State lock remains after failed plan/apply
**Fix**: `terraform force-unlock <LOCK_ID>`

### 4. AgentCore Memory Mode
**Issue**: `mode=read_write` fails with "STM is read only"
**Fix**: Use `memory_manager(mode=MemoryMode.READ_ONLY)` for now (write pending AWS fix)

### 5. Button UX Global Fix (January 2026)
**Issue**: All buttons lacked cursor feedback, hover states, and click effects
**Fix**: Updated `button.tsx` CVA and `globals.css` with:
- `cursor: pointer` global for all clickable elements
- Hover: `brightness(1.1)` + `translateY(-0.5)`
- Active/Press: `scale(0.98)` with 34ms duration (2 frames at 60fps)
- `motion-reduce:` variants for accessibility
```tsx
// button.tsx now includes these classes
"cursor-pointer",
"hover:-translate-y-0.5 hover:brightness-110",
"active:scale-[0.98] active:brightness-95 active:duration-[34ms]",
"motion-reduce:transition-none"
```

### 6. Smart Import TypeScript Patterns (January 2026)
**Issue**: TypeScript exhaustiveness checks on discriminated unions in preview components
**Fix**: Use type guards and explicit casts for fallback cases
```typescript
// Type guards for discriminated union
export function isNFImportResult(preview: SmartImportPreview): preview is NFImportResult {
  return ['nf_xml', 'nf_pdf', 'nf_image'].includes(preview.source_type);
}

// Fallback for never type (unreachable but needed for exhaustiveness)
const unknownPreview = preview as SmartImportPreview;
```
**Also**: Lucide icons don't accept `title` prop - use `aria-label` instead
