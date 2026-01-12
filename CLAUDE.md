# CLAUDE.md

This file provides **GLOBAL, NON-NEGOTIABLE guidance** to Claude Code (`claude.ai/code`) when working in this repository.

To be used on web research we are in year 2026.

---

<!-- ===================================================== -->
<!-- 🔒 IMMUTABLE BLOCK – DO NOT MODIFY OR REMOVE 🔒       -->
<!-- THIS SECTION IS PERMANENT AND NON-NEGOTIABLE          -->
<!-- ANY CHANGE, REMOVAL, OR REWRITE IS STRICTLY FORBIDDEN -->
<!-- ===================================================== -->

## 🔒 [IMMUTABLE][DO-NOT-REMOVE][AI-FIRST][AGENTIC][AWS Strands][BEDROCK-AGENTCORE]

- ALL agents MUST be created using the **AWS STRANDS AGENTS FRAMEWORK**.
- YOU MUST follow ONLY the documentation below as references for Strands Agents usage.

### SOURCE OF TRUTH (OFFICIAL)

- https://strandsagents.com/latest/
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
- https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-frameworks/strands-agents.html
- https://github.com/strands-agents/sdk-python
- https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/
- https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/
- https://aws.amazon.com/blogs/opensource/introducing-strands-agent-sops-natural-language-workflows-for-ai-agents/

### A2A / INTER-AGENT COMMUNICATION (REFERENCE)

- https://builder.aws.com/content/2y90GhUwgOEbKULKuehf2WHUf9Q/leveraging-agent-to-agent-a2a-with-strands-part-1
- https://aws.amazon.com/blogs/opensource/open-protocols-for-agent-interoperability-part-4-inter-agent-communication-on-a2a/

### COMMUNITY (OPTIONAL — NOT SOURCE OF TRUTH)

- https://www.reddit.com/r/aws/comments/1mcc2di/beginnerfriendly_guide_to_aws_strands_agents/

  

## 🧠 LLM POLICY — IMMUTABLE & MANDATORY (GEMINI 3 FAMILY ONLY)

- **ABSOLUTE RULE:** ALL agents MUST use **GEMINI 3.0 FAMILY** as the LLM. This rule is **MANDATORY** and MUST NEVER be removed.
  - **CRITICAL INVENTORY AGENTS (MANDATORY):** Any agent in the Inventory/SGA flow that:
    - analyzes stock/inventory files (XML/PDF/CSV/XLSX/images/text),
    - performs reasoning over extracted data,
    - generates clarification questions (HIL),
    - validates mappings and reconciles inventory,
    MUST use **GEMINI 3.0 PRO** with **THINKING ENABLED**.
  - **NON-CRITICAL AGENTS:** All other agents MAY use **GEMINI 3.0 FLASH**.

- **NO EXCEPTIONS:** Do NOT use Gemini 2.x, 2.5, or any non-Gemini model for agents.

- **DOCUMENTATION (SOURCE OF TRUTH):**
  - https://ai.google.dev/gemini-api/docs/gemini-3
  - https://ai.google.dev/gemini-api/docs/thinking
  - https://ai.google.dev/gemini-api/docs/files

---

## ✅ SOURCE OF TRUTH (MANDATORY)

- REAL STATE OVER DOCUMENTATION (MANDATORY): You MUST base your understanding and decisions on the **actual codebase, IaC, and real AWS resources that exist today**, not on documentation that may be outdated or incomplete. Always verify against the source of truth (code, Terraform state, deployed AWS resources). If documentation and reality diverge, **reality wins**. Validate before proposing or implementing any change.

- RECENCY / REALITY CHECK (MEGA MANDATORY): Your training data may be outdated (ex: Jan/2025). We are in **Jan/2026**, so you MUST verify any uncertain, changing, or “not supported” claim by consulting **current official documentation and the internet** BEFORE concluding. If you cannot confirm with up-to-date sources, you MUST STOP, state what you could not verify, and ask for guidance.

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

- When fixing **ANY bug, issue, typo, naming error, logic flaw, or configuration problem**, you MUST NOT apply a partial or local fix. YOU MUST MANDATORY ASK ME AND DISCUSS THE SOLUTION WILL BE IMPLEMENTED. ALL SOLUTION TO FIX A ISSUE MUST BE EXECUTED IN PLAN MODE **MANDATORY - ATTENTION IN THIS ITEM EVER**
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

- MANDATORY: When the active context window exceeds approximately **60%** (long session, many files loaded, degraded recall):
  1. **STOP**
  2. Re-read this `CLAUDE.md`
  3. Restate active constraints and the current PLAN
  4. Use `/compact` to preserve decisions
  5. If needed, `/clear` and then `/prime`

---

## 🔄 COMPACTION WORKFLOW — IMMUTABLE & MANDATORY

- Before ANY context compaction (`/compact` or automatic compaction), you MUST run `/sync-project` FIRST to persist the real project state (docs + code + IaC + AWS reality) into memory and references.
- After compaction, you MUST re-run `/prime` (or an equivalent post-compact prime injection) to reload `CLAUDE.md` rules and current project context.
- If `/sync-project` was not executed before compaction, compaction MUST be blocked.

---

## 🪝 HOOKS ENFORCEMENT — MANDATORY (Continuous Prime)

- Claude Code Hooks MUST be enabled to enforce continuous rule priming and continuous session context:
  - `UserPromptSubmit` MUST inject essential rules from `CLAUDE.md` (prefer IMMUTABLE block) AND inject the current living context from `docs/CONTEXT_SNAPSHOT.md`.
  - `Stop` MUST update `docs/CONTEXT_SNAPSHOT.md` after every response (post-turn context refresh) AND append to `docs/WORKLOG.md` (audit trail).
  - If the post-turn update fails, the Stop hook MUST **BLOCK** completion (unless `CLAUDE_HOOKS_ALLOW_FAIL=true` is explicitly set as a temporary override).
  - Hook implementation details live in `docs/Claude Code/HOOKS.md`.

---

## 🧠 AGENT EXECUTION FLOW (IMMUTABLE & MEGA MANDATORY)

- ALL agents MUST follow the operational loop: **OBSERVE → THINK → LEARN → ACT (EXECUTE)**.
- **HUMAN-IN-THE-LOOP (HIL) IS ALWAYS PART OF THE PROCESS**:
  - Agents MUST request approval when confidence is low, when actions are high-impact, or when policy requires it.
  - Agents MUST NOT execute irreversible or risky actions without explicit HIL approval.
- This loop is NOT optional. Any agent behavior that skips OBSERVE/THINK/LEARN or bypasses HIL is **WRONG** and MUST be corrected.

---

## 🚫 NON-AGENT ARCHITECTURE IS FORBIDDEN

- USING **AI AGENTS IS 100% MANDATORY**.
- DO NOT design or implement traditional serverless Lambda microservices.
- DO NOT use client-server, REST-only, or function-oriented architectures.
- Lambda is allowed **ONLY** as an execution substrate required by **AWS Bedrock AgentCore**.
- IF you are about to design a “normal Lambda service” → **STOP IMMEDIATELY**.
- DO NOT IMPLEMENTE ANY TRADITIONAL SOFTWARE ORIENTED OBJECT ARCHITETCURE. THIS IS A AGENTIC SOLUTION.

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
- AWS CLI PROFILE (MANDATORY): For ANY AWS CLI command, you MUST use the correct AWS profile from the **AWS CONFIGURATION** section (right account + region). Never run AWS CLI commands without explicitly setting/confirming the profile (e.g., `--profile <profile>`). If the profile is unknown or not configured, STOP and ask before proceeding.
- To check AWS Bedrock AgentCore configurations and make CLI change to AgentCore use the AgentCore CLI  
  https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html

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

### MCP + Documentation

- **MCP ACCESS POLICY:**  
  ALL MCP tools and servers MUST be accessed ONLY via **AWS Bedrock AgentCore Gateway**.

- **DOCUMENTATION CHECK POLICY:**  
  Before implementing ANY AWS, AgentCore, MCP, or IaC code, you MUST consult:
  - AWS AgentCore documentation
  - MCP AWS documentation
  - MCP Context7 documentation  
  If unclear → **STOP AND ASK**.

### AWS STRANDS AGENTS — DOCUMENTATION (MANDATORY)

- **OFFICIAL / PRIMARY SOURCES (SOURCE OF TRUTH):**
  - https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/
  - https://strandsagents.com/latest/
  - https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-frameworks/strands-agents.html
  - https://github.com/strands-agents/sdk-python
  - https://aws.amazon.com/blogs/opensource/introducing-strands-agent-sops-natural-language-workflows-for-ai-agents/
  - https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/

- **A2A / MULTI-AGENT (REFERENCE):**
  - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
  - https://builder.aws.com/content/2y90GhUwgOEbKULKuehf2WHUf9Q/leveraging-agent-to-agent-a2a-with-strands-part-1
  - https://aws.amazon.com/blogs/opensource/open-protocols-for-agent-interoperability-part-4-inter-agent-communication-on-a2a/

- **COMMUNITY (OPTIONAL — NOT SOURCE OF TRUTH):**
  - https://www.reddit.com/r/aws/comments/1mcc2di/beginnerfriendly_guide_to_aws_strands_agents/

### Lambda + Terraform

- **LAMBDA RUNTIME POLICY:**  
  ALL AWS Lambda functions MUST use:
  - Architecture: `arm64`
  - Runtime: `Python 3.13`

- **TERRAFORM DOCS POLICY:**  
  Use the official Terraform Registry as source of truth:
  - https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_gateway
  - https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime

### SDLC + Security

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

### Inventory Datastore

- **INVENTORY DATASTORE — CRITICAL:**  
  Inventory data MUST live in **AWS Aurora PostgreSQL (RDS)**.  
  **DO NOT USE DynamoDB**.  
  Any assumption otherwise is **WRONG** and MUST be fixed.

**MCP**

- BEDROCK AGENTCORE MCP (MANDATORY): For communicating, testing, validating, and invoking tools, you MUST use **Amazon Bedrock AgentCore via MCP**:
  - Use **AgentCore Gateway MCP endpoint** for tool discovery/invocation (`tools/list`, `tools/call`) — do NOT call tool endpoints directly.
  - Use the **AgentCore MCP Server** in the development environment when you need to transform, deploy, and test AgentCore-compatible agents from your MCP client (Claude Code/Cursor/etc.).

---

## 🛠️ TOOLING ENFORCEMENT — IMMUTABLE & MEGA MANDATORY

- For EVERY development task, Claude Code MUST use **SubAgents**, relevant **Skills**, and MUST consult the required **MCP sources** (Context7 + AWS Documentation + Bedrock AgentCore + Terraform MCP + any other project MCP) before coding or changing anything.
- SubAgents are NOT optional — use them by default for parallel execution and specialization.
- If you are about to proceed without SubAgents or without the required MCP documentation checks, you MUST STOP IMMEDIATELY and ask for explicit approval.

---

## 🧭 EXECUTION DISCIPLINE — MANDATORY

- CONTEXT FIRST (MANDATORY): First think through the problem and read the codebase (relevant files) before proposing or implementing a solution.
- MAJOR CHANGES REQUIRE APPROVAL (MANDATORY): Before making any major change (architecture, refactor, broad behavior change), you MUST check in with me and get explicit approval of the plan.
- HIGH-LEVEL CHANGE SUMMARY (MANDATORY): At every step, provide a short high-level explanation of what you changed and why (no long essays).
- SIMPLICITY FIRST (MANDATORY): Keep every task and code change as simple as possible. Avoid massive or complex changes. Each change should impact as little code as possible.
- ARCHITECTURE DOCUMENTATION (MANDATORY): Maintain a documentation file that describes the application architecture end-to-end (how it works inside and out). Keep it updated when architecture changes.
- NO SPECULATION / READ BEFORE ANSWERING (MANDATORY): Never speculate about code you have not opened. If a specific file is referenced, you MUST read it before answering. Investigate and read relevant files BEFORE making any claim. Provide grounded, hallucination-free answers; if uncertain, say so and read more before proceeding.

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

- ALWAYS use Claude Code SubAgents and Skills in all taks or debugs. THIS IS MANDATORY
- Use `prompt-engineer` SubAgent to improve prompts. MANDATORY

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

## 🧼 CLAUDE.md HYGIENE — MANDATORY

- Root `CLAUDE.md` is GLOBAL POLICIES ONLY. Routes/components/endpoints/known-issues MUST go to `docs/` or module `CLAUDE.md` files. Do NOT bloat root memory.

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

- **RULE OF THUMB:**  
  If you cannot clearly explain **why something was built the way it is**, you are **NOT ALLOWED** to change it.

- **ENFORCEMENT:**  
  If a change was made without proper context understanding or impact analysis, it MUST be considered **INVALID**, reverted if necessary, and you MUST **STOP AND ASK FOR GUIDANCE** before proceeding.



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
