# CORE IMMUTABLE RULES

> These rules are GLOBAL, NON-NEGOTIABLE, and apply to ALL files in this repository.
> ANY modification, removal, or rewrite of this file is STRICTLY FORBIDDEN.

## Source of Truth Policy

- **REAL STATE OVER DOCUMENTATION:** Base understanding on actual codebase, IaC, and real AWS resources—not outdated docs. If documentation and reality diverge, reality wins.
- **RECENCY CHECK:** Training data may be outdated (Jan/2025). We are in 2026. Verify uncertain claims with current official documentation BEFORE concluding.

## AI-First Platform Identity

- **FAISTON ONE** is a 100% AUTONOMOUS and GENERATIVE AI agent system
- This is NOT a traditional client-server or microservices system
- This is a 100% AI-FIRST and AGENTIC platform
- Agents automate cognitive tasks, learn from context/feedback, provide recommendations, and continuously improve

## Agent Execution Flow

ALL agents MUST follow: **OBSERVE → THINK → LEARN → ACT (EXECUTE)**

- **HUMAN-IN-THE-LOOP (HIL)** is always part of the process
- Agents MUST request approval when confidence is low or actions are high-impact
- Agents MUST NOT execute irreversible actions without explicit HIL approval

## Forbidden Architectures

- **NO traditional serverless Lambda microservices**
- **NO client-server, REST-only, or function-oriented architectures**
- **NO object-oriented traditional software architecture**
- Lambda is allowed ONLY as execution substrate for AWS Bedrock AgentCore
- If designing a "normal Lambda service" → STOP IMMEDIATELY

## Bugfix & Consistency Protocol

- When fixing ANY bug/issue, **DO NOT apply partial fixes**
- MUST discuss solution in PLAN MODE before implementation
- After correction, validate ENTIRE codebase: code, imports, configs, tests, scripts, docs
- If unsure → STOP AND ASK

## No Speculation Policy

- NEVER speculate about code you have not opened
- If a file is referenced, READ IT before answering
- Provide grounded, hallucination-free answers
- If uncertain → read more → if still uncertain → ASK

## Enforcement

If ANY immutable rule is modified/removed/rewritten:
1. STOP IMMEDIATELY
2. ASK FOR EXPLICIT APPROVAL
3. EXPLAIN WHY
