# CLAUDE.md

This file provides **GLOBAL, NON-NEGOTIABLE guidance** to Claude Code (`claude.ai/code`) when working in this repository. 

To be used on web research we are in year 2026.

> **MEMORY ARCHITECTURE (CRITICAL):**  
> This root `CLAUDE.md` contains **ONLY essential global rules**.  
> Context-specific or module-level details MUST live in subdirectory `CLAUDE.md` files (lazy-loaded).

---

<!-- ===================================================== -->
<!-- 🔒 IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE 🔒       -->
<!-- THIS SECTION IS PERMANENT AND NON-NEGOTIABLE          -->
<!-- ANY CHANGE, REMOVAL, OR REWRITE IS STRICTLY FORBIDDEN -->
<!-- ===================================================== -->

## 🔒 [IMMUTABLE][DO-NOT-REMOVE][AI-FIRST][AGENTIC][GOOGLE-ADK][BEDROCK-AGENTCORE]

---

- REAL STATE OVER DOCUMENTATION (MANDATORY): You MUST base your understanding and decisions on the **actual codebase, IaC, and real AWS resources that exist today**, not on documentation that may be outdated or incomplete. Always verify against the source of truth (code, Terraform state, deployed AWS resources). If documentation and reality diverge, **reality wins**. Validate before proposing or implementing any change.

---
## 🧠 FAISTON ONE — MANDATORY CONTEXT

- **FAISTON ONE** is a **100% AUTONOMOUS** and **GENERATIVE** AI agent system.
- Agents:
  - Automate cognitive tasks
  - Learn from context and feedback
  - Provide opinions and recommendations
  - Continuously improve processes
- Agents improve **memory and knowledge** using **reinforcement learning techniques** and learning loops aligned with the platform architecture.

- This is **NOT** a traditional client-server or microservices system.
- This is a **100% AI-FIRST** and **AGENTIC** platform.
- If you do NOT understand what **AI-FIRST** means, you MUST research and fully understand it **BEFORE** designing or implementing anything.

---

## 🐛 BUGFIX & CONSISTENCY CHECK — MANDATORY

- When fixing **ANY bug, issue, typo, naming error, logic flaw, or configuration problem**, you MUST NOT apply a partial or local fix.
- After making a correction, you MUST validate the **ENTIRE codebase**:
  - code
  - imports
  - constants
  - configs
  - tests
  - scripts
  - documentation
- A fix is **INCOMPLETE** until global consistency is verified.
- If unsure → **STOP AND ASK BEFORE PROCEEDING**.

---

## 🧠 CONTEXT WINDOW MANAGEMENT — MANDATORY

- When the active context window exceeds approximately **60%** (long session, many files loaded, degraded recall):
  1. **STOP**
  2. Re-read this `CLAUDE.md`
  3. Restate active constraints and the current PLAN
  4. Use `/compact` to preserve decisions
  5. If needed, `/clear` and then `/prime`

---

## 🚫 NON-AGENT ARCHITECTURE IS FORBIDDEN

- USING **AI AGENTS IS 100% MANDATORY**.
- DO NOT design or implement traditional serverless Lambda microservices.
- DO NOT use client-server, REST-only, or function-oriented architectures.
- Lambda is allowed **ONLY** as an execution substrate required by **AWS Bedrock AgentCore**.
- IF you are about to design a “normal Lambda service” → **STOP IMMEDIATELY**.

---

## 🔐 AUTHENTICATION POLICY — MANDATORY

- **NO AWS AMPLIFY** — EVER.
- **Amazon Cognito** is the PRIMARY authentication method.
- Direct API usage only.
- NO SDK abstractions.

---

## ☁️ AWS CONFIGURATION — MANDATORY

- AWS Account ID: `377311924364`
- AWS Region: `us-east-2`

---

## 🏗️ INFRASTRUCTURE POLICY — MANDATORY

### ❌ NEVER DO
1. CloudFormation or SAM (Terraform ONLY)
2. Parallel environments without consolidation
3. Duplicate CORS (ONLY in `terraform/main/locals.tf`)
4. Hardcoded AWS values
5. Local deployments

### ✅ ALWAYS DO
1. Use Terraform for **ALL AWS resources**
2. Apply **ALL CORS changes ONLY** in `terraform/main/locals.tf`
3. Run `terraform plan` via GitHub Actions **BEFORE** apply

---

## 🌍 ADDITIONAL GLOBAL POLICIES — MANDATORY

- **MCP ACCESS POLICY:**  
  ALL MCP tools and servers MUST be accessed ONLY via **AWS Bedrock AgentCore Gateway**.

- **DOCUMENTATION CHECK POLICY:**  
  Before implementing ANY AWS, AgentCore, MCP, or IaC code, you MUST consult:
  - AWS AgentCore documentation
  - MCP AWS documentation
  - MCP Context7 documentation  
  If unclear → **STOP AND ASK**.

- **LAMBDA RUNTIME POLICY:**  
  ALL AWS Lambda functions MUST use:
  - Architecture: `arm64`
  - Runtime: `Python 3.13`

- **TERRAFORM DOCS POLICY:**  
  Use the official Terraform Registry as source of truth:
  - https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_gateway
  - https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime

- **SDLC + CLEAN CODE:**  
  Follow state-of-the-art SDLC and Clean Code practices:
  - code reviews
  - automated tests
  - CI/CD
  - linting/formatting
  - maintainable code

- **SECURITY / PENTEST-READY:**  
  Platform MUST be security-first and aligned with:
  - OWASP
  - NIST CSF
  - MITRE ATT&CK
  - CIS
  - AWS Security
  - AWS Well-Architected Security Pillar
  - Microsoft SDL

- **INVENTORY DATASTORE — CRITICAL:**  
  Inventory data MUST live in **AWS Aurora PostgreSQL (RDS)**.  
  **DO NOT USE DynamoDB**.  
  Any assumption otherwise is **WRONG** and MUST be fixed.

---
- CONTEXT FIRST (MANDATORY): First think through the problem and read the codebase (relevant files) before proposing or implementing a solution.

- MAJOR CHANGES REQUIRE APPROVAL (MANDATORY): Before making any major change (architecture, refactor, broad behavior change), you MUST check in with me and get explicit approval of the plan.

- HIGH-LEVEL CHANGE SUMMARY (MANDATORY): At every step, provide a short high-level explanation of what you changed and why (no long essays).

- SIMPLICITY FIRST (MANDATORY): Keep every task and code change as simple as possible. Avoid massive or complex changes. Each change should impact as little code as possible.

- ARCHITECTURE DOCUMENTATION (MANDATORY): Maintain a documentation file that describes the application architecture end-to-end (how it works inside and out). Keep it updated when architecture changes.

- NO SPECULATION / READ BEFORE ANSWERING (MANDATORY): Never speculate about code you have not opened. If a specific file is referenced, you MUST read it before answering. Investigate and read relevant files BEFORE making any claim. Provide grounded, hallucination-free answers; if uncertain, say so and read more before proceeding.


---
## 🚨 AGENTCORE COLD START LIMIT — CRITICAL

- Cold start limit: **30 seconds**
- Violations cause **HTTP 424** and break AI features.

### ❌ NEVER DO
1. Heavy dependencies (`lxml`, `beautifulsoup4`, etc.)
2. Imports in `agents/__init__.py` or `tools/__init__.py`
3. Agent imports at module level

### ✅ ALWAYS DO
1. Minimal `requirements.txt`
2. Lazy imports inside handlers
3. Use Python stdlib (`xml.etree.ElementTree`)
4. Check AgentCore pre-installed libraries

---

## 📌 PRIMARY INSTRUCTIONS

- NEVER create files in root unless absolutely necessary
- ALL documentation lives in `docs/`
- Be extremely concise
- ALWAYS create a PLAN before implementation

## Git & GitHub

- Use GitHub CLI
- Branch prefix: `fabio/`

## SubAgents & Skills

- ALWAYS use Claude Code SubAgents and Skills
- Use `prompt-engineer` SubAgent to improve prompts

---

## 🚨 ENFORCEMENT RULE

- IF ANY PART OF THIS IMMUTABLE BLOCK IS:
  - Modified
  - Removed
  - Rewritten
  - Summarized
  - Relocated

  THEN:
  - YOU MUST **STOP IMMEDIATELY**
  - YOU MUST **ASK FOR EXPLICIT APPROVAL**
  - YOU MUST **EXPLAIN WHY**

---
- CLAUDE.md HYGIENE (MANDATORY): Root `CLAUDE.md` is GLOBAL POLICIES ONLY. Routes/components/endpoints/known-issues MUST go to `docs/` or module `CLAUDE.md` files. Do NOT bloat root memory.

---

## 🧠 AGENTCORE MEMORY MODEL — IMMUTABLE & MANDATORY

- **CLARIFICATION (MANDATORY):** Agents in this system run on **AWS Bedrock AgentCore**, **NOT** on traditional AWS Lambda microservices.
  - AgentCore provides its **OWN MANAGED MEMORY SYSTEM**.
  - Agents MUST use **AgentCore Memory** and its defined lifecycle, strategies, and APIs.

- **FORBIDDEN:**  
  - Treating agents as stateless Lambdas  
  - Implementing custom memory outside AgentCore without explicit approval  
  - Bypassing or re-implementing AgentCore memory mechanisms

- **MANDATORY MEMORY USAGE:**  
  All agents MUST follow the **AgentCore Memory model**, including:
  - Session Memory
  - Short-Term Memory (STM)
  - Long-Term Memory (LTM)
  - Retrieval-Augmented Generation (RAG) where applicable
  - Built-in or approved custom memory strategies

- **SOURCE OF TRUTH (MANDATORY READING):**  
  You MUST consult and follow the official AWS Bedrock AgentCore Memory documentation:
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-terminology.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-types.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-strategies.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/built-in-strategies.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-custom-strategy.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-self-managed-strategies.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-organization.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-ltm-rag.html

- **REFERENCE MATERIAL (OPTIONAL BUT RECOMMENDED):**
  - https://www.aboutamazon.com/news/aws/aws-amazon-bedrock-agent-core-ai-agents
  - https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-memory-building-context-aware-agents/
  - https://strandsagents.com/latest/documentation/docs/community/session-managers/agentcore-memory/
  - https://www.youtube.com/watch?v=-N4v6-kJgwA
  - https://levelup.gitconnected.com/bedrock-agentcore-part2-memory-raw-database-vector-store-some-eventbridge-ish-logics-594aad0389c0

- **ENFORCEMENT:**  
  If you design, implement, or describe agent memory outside the AgentCore memory model, you MUST **STOP IMMEDIATELY** and **ASK FOR EXPLICIT APPROVAL**.
---
## 🧠 CONTEXT AWARENESS & IMPACT ANALYSIS — IMMUTABLE & MANDATORY

- **YOU MUST NOT CHANGE ANYTHING** (code, docs, commands, architecture, configuration, naming, structure) **WITHOUT FIRST FULLY UNDERSTANDING**:
  - WHAT you are changing
  - WHY it exists
  - HOW it is used
  - WHERE it is referenced
  - WHAT OTHER SYSTEMS, MODULES, OR COMMANDS MAY BE AFFECTED

- **FORBIDDEN BEHAVIOR**:
  - Making changes “to improve” without understanding context
  - Refactoring or simplifying without impact analysis
  - Changing commands (`prime`, `sync-project`, etc.) without understanding their original purpose
  - Assuming intent instead of reading documentation and code
  - Changing behavior because “it seems better”

- **MANDATORY BEFORE ANY CHANGE**:
  1. Read the relevant documentation (`CLAUDE.md`, `prime.md`, `sync-project.md`, docs/)
  2. Understand the ORIGINAL INTENT of the code or rule
  3. Identify ALL dependencies and side effects
  4. State explicitly what will change and what will NOT change
  5. Only then implement

- **RULE OF THUMB**:  
  If you cannot clearly explain **why something was built the way it is**, you are **NOT ALLOWED** to change it.

- **ENFORCEMENT**:  
  If a change was made without proper context understanding or impact analysis, it MUST be considered **INVALID**, reverted if necessary, and you MUST **STOP AND ASK FOR GUIDANCE** before proceeding.

---

- CONTEXT FIRST (MANDATORY): First think through the problem and read the codebase (relevant files) before proposing or implementing a solution.

- MAJOR CHANGES REQUIRE APPROVAL (MANDATORY): Before making any major change (architecture, refactor, broad behavior change), you MUST check in with me and get explicit approval of the plan.

- HIGH-LEVEL CHANGE SUMMARY (MANDATORY): At every step, provide a short high-level explanation of what you changed and why (no long essays).

- SIMPLICITY FIRST (MANDATORY): Keep every task and code change as simple as possible. Avoid massive or complex changes. Each change should impact as little code as possible.

- ARCHITECTURE DOCUMENTATION (MANDATORY): Maintain a documentation file that describes the application architecture end-to-end (how it works inside and out). Keep it updated when architecture changes.

- NO SPECULATION / READ BEFORE ANSWERING (MANDATORY): Never speculate about code you have not opened. If a specific file is referenced, you MUST read it before answering. Investigate and read relevant files BEFORE making any claim. Provide grounded, hallucination-free answers; if uncertain, say so and read more before proceeding.

---

## 📦 SGA MODULE ARCHITECTURE — IMMUTABLE & MANDATORY

> **Sistema de Gestão de Ativos (SGA)** is the reference architecture for ALL new modules.

- **MANDATORY READING BEFORE ANY SGA WORK:**
  You MUST read and follow the official architecture document:
  - `docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md`

- **SGA ARCHITECTURAL PATTERNS (MANDATORY):**
  All SGA implementations MUST follow these patterns:

  1. **Context Provider Hierarchy:**
     ```
     QueryClientProvider → AssetManagementProvider → InventoryOperationsProvider
       → TaskInboxProvider → NexoEstoqueProvider → InventoryCountProvider → OfflineSyncProvider
     ```
     - Reference: `client/app/(main)/ferramentas/ativos/layout.tsx`

  2. **Hook Organization:**
     - Data fetching hooks: `useAssets`, `useMovements`, `useLocations`, `usePartNumbers`, `useProjects`
     - Operation hooks: `useMovementMutations`, `useMovementValidation`
     - Import hooks: `useSmartImporter`, `useNFReader`, `useBulkImport`
     - Reference: `client/hooks/ativos/`

  3. **Service Layer Pattern:**
     - All backend calls via `sgaAgentcore.ts` service
     - JWT Bearer token auth with AgentCore Gateway
     - Session management with sessionStorage
     - Reference: `client/services/sgaAgentcore.ts`

  4. **Smart Import Architecture:**
     - File type detection via magic bytes (`file_detector.py`)
     - Route to appropriate agent: IntakeAgent (NF), ImportAgent (spreadsheet)
     - Confidence-based HIL routing (≥80% = autonomous, <80% = HIL review)
     - Reference: `client/hooks/ativos/useSmartImporter.ts`

  5. **NEXO AI Copilot Pattern:**
     - Frosted glass FAB with sliding panel (Apple TV style)
     - Quick actions (7 predefined queries)
     - KB integration with citations
     - Reference: `client/components/ferramentas/ativos/estoque/nexo/`

  6. **Offline-First (PWA):**
     - Queue-based sync with localStorage persistence
     - Auto-retry with exponential backoff (max 3 retries)
     - Reference: `client/contexts/ativos/OfflineSyncContext.tsx`

  7. **Schema Evolution Pattern:**
     - Dynamic column creation via Schema Evolution Agent (SEA)
     - ALL schema changes via MCP Gateway (never direct DB connections)
     - JSONB `metadata` column fallback when column creation fails
     - Advisory locking (`pg_advisory_xact_lock`) for concurrent modifications
     - Reference: `server/agentcore-inventory/agents/schema_evolution_agent.py`

- **KEY FILE REFERENCES:**
  - **Types**: `client/lib/ativos/types.ts`
  - **Constants**: `client/lib/ativos/constants.ts`
  - **Smart Import Types**: `client/lib/ativos/smartImportTypes.ts`
  - **Backend Main**: `server/agentcore-inventory/main.py`
  - **Backend Agents**: `server/agentcore-inventory/agents/`
  - **DB Migrations**: `server/agentcore-inventory/schema/` (numbered: `001_*.sql`, `002_*.sql`, ...)

- **ENFORCEMENT:**
  If you implement SGA features without following this architecture, you MUST **STOP IMMEDIATELY** and **CONSULT THE ARCHITECTURE DOC**.

---

## 🧠 CONTEXT ENGINEERING — IMMUTABLE & MANDATORY (Best Practices 2025-2026)

> Based on [Anthropic's Context Engineering Guide](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) and [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices).

- **TOKEN EFFICIENCY (MANDATORY):**
  - Context is a **FINITE RESOURCE** — every token competes for attention
  - Prefer **pointers to copies**: Use `file:line` references, not code snippets
  - Use **progressive disclosure**: Load context just-in-time, not upfront
  - If context exceeds **60% capacity** → `/compact` or `/clear` + `/prime`

- **INSTRUCTION LIMITS (MANDATORY):**
  - LLMs can follow **~150-200 instructions** with reasonable consistency
  - This `CLAUDE.md` already contains ~50+ instructions
  - **DO NOT** add task-specific instructions here
  - **DO** add task-specific guidance in `docs/` and reference with `@docs/filename.md`

- **STRUCTURE PRINCIPLE (MANDATORY):**
  - Follow **WHAT** (tech stack, structure) / **WHY** (purpose) / **HOW** (process) model
  - Use clear section headers (`## SECTION_NAME`)
  - Separate instructions from context

- **TOOL DELEGATION (MANDATORY):**
  - **NEVER** send an LLM to do a linter's job → Use Biome, ESLint, ruff
  - Use `/check` skill for lint + build + test validation
  - Reserve AI for reasoning tasks, not mechanical validation

- **UNCERTAINTY HANDLING (MANDATORY):**
  - **EXPRESS UNCERTAINTY** rather than guessing → reduces hallucinations
  - If unsure → **READ MORE FILES** before proceeding
  - If still unsure → **ASK THE USER**

- **COMPACTION STRATEGY (MANDATORY):**
  - When nearing context limits, summarize and restart
  - Preserve: architectural decisions, unresolved issues
  - Discard: redundant tool outputs, verbose logs
  - Use structured notes (`NOTES.md`, `TODO.md`) for long tasks

- **SUB-AGENT ARCHITECTURE (MANDATORY):**
  - Use specialized agents for focused tasks
  - Return **condensed summaries** (1,000-2,000 tokens) to parent agent
  - Reference: Available SubAgents in Claude Code Skills

---

## 📚 PROGRESSIVE DISCLOSURE — IMMUTABLE & MANDATORY

> Module-specific details MUST live in subdirectory docs, not in root CLAUDE.md.

- **ARCHITECTURE DOCS (Reference as needed):**
  - SGA Module: `docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md`
  - AgentCore Implementation: `docs/AgentCore/IMPLEMENTATION_GUIDE.md`
  - Frontend Auth: `docs/FRONTEND_AUTH.md`
  - Agent Design: `docs/agents/ADK_AGENTCORE_ARCHITECT.md`

- **PRD DOCS (Reference for requirements):**
  - SGA Estoque PRD: `docs/prd_modulo_gestao_estoque_faiston_sga2.md`
  - Inventory Management: `docs/Faiston_Investory_Mamagement.md`

- **SETUP DOCS (Reference for configuration):**
  - Equipment KB Setup: `docs/SGA_EQUIPMENT_KB_SETUP.md`

- **USAGE PATTERN:**
  - Before implementing a feature → `@docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md`
  - Before AgentCore work → `@docs/AgentCore/IMPLEMENTATION_GUIDE.md`
  - When unsure about patterns → Read the relevant doc **FIRST**

---

## 🔄 FLYWHEEL IMPROVEMENT — IMMUTABLE & MANDATORY

> Treat CLAUDE.md as a living document that improves over time.

- **DATA-DRIVEN UPDATES:**
  - Review logs for common mistakes → Update CLAUDE.md
  - Pattern: **Bugs → Improved CLAUDE.md / Skills → Better Agent**

- **ADDING NEW RULES:**
  1. Identify recurring mistake or pattern
  2. Propose rule addition with justification
  3. Add to appropriate section (NOT root if module-specific)
  4. Test rule effectiveness over 3+ sessions

- **FORBIDDEN:**
  - Adding rules without observed need
  - Adding code snippets (use file:line references instead)
  - Adding task-specific instructions to root CLAUDE.md

---
<!-- ===================================================== -->
<!-- 🔒 END OF IMMUTABLE BLOCK                             -->
<!-- ===================================================== -->
