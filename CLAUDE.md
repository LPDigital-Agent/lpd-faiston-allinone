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
│   └── resources/         # Templates and product overview
├── client/                 # Next.js 15 frontend (App Router)
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   │   ├── ui/           # shadcn/ui library
│   │   └── ferramentas/  # Ferramentas modules
│   │       └── academy/  # Faiston Academy (migrated from Hive Academy)
│   │           ├── classroom/  # 14 floating panels
│   │           └── dashboard/  # 5 dashboard components
│   ├── contexts/          # React contexts (Academy*, etc.)
│   ├── hooks/             # Custom hooks
│   │   └── academy/      # 11 Academy-specific hooks
│   ├── lib/               # Utilities
│   │   └── academy/      # Academy types, constants
│   └── services/          # API clients (academyAgentcore.ts, etc.)
├── server/                 # Python backend
│   └── agentcore-academy/ # Faiston Academy AgentCore agents
│       ├── main.py        # BedrockAgentCoreApp entrypoint (19 actions)
│       ├── agents/        # Google ADK Agents (NEXO, flashcards, mindmap, etc.)
│       └── tools/         # Agent tools (elevenlabs, heygen, youtube)
└── terraform/             # AWS Infrastructure as Code
    └── main/              # Academy resources (Cognito, S3, DynamoDB, IAM)
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

### Academy Hooks (11)
`client/hooks/academy/`: useNexoAI, useFlashcards, useMindMap, useAudioClass, useSlideDeck, useReflection, useFloatingPanel, useExtraClass, useVideoClass, useYouTubeRecommendations, index

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