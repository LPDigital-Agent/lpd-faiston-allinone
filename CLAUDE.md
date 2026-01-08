# CLAUDE.md

This file provides **GLOBAL, NON-NEGOTIABLE guidance** to Claude Code (`claude.ai/code`) when working in this repository.

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

<!-- ===================================================== -->
<!-- 🔒 END OF IMMUTABLE BLOCK                             -->
<!-- ===================================================== -->