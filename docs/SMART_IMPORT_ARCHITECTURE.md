# Smart Import Architecture (NEXO)

> **MANDATORY REFERENCE**: This document describes the complete Smart Import flow.
> Claude Code MUST consult this document before making any changes to the import flow.

---

## Overview

Smart Import is an **AI-First** file import system that uses:
- **Gemini 3.0 Pro with Thinking** for intelligent column mapping
- **Multi-Round Human-in-the-Loop (HIL)** dialogue for ambiguity resolution
- **AWS Bedrock AgentCore** for agent hosting and orchestration
- **A2A Protocol** for inter-agent communication

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React/Next.js)                   │
│  /ferramentas/ativos/estoque/movimentacoes/importar/           │
│                                                                 │
│  useBulkImport hook → sgaAgentcore.ts → agentcoreBase.ts       │
│                                                                 │
│  Authentication: JWT Bearer Token (Cognito)                     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ POST /runtimes/{ARN}/invocations
                                  │ Authorization: Bearer {JWT}
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              AWS BEDROCK AGENTCORE (HTTP Protocol)              │
│         faiston_asset_management-uSuLPsFQNH                     │
│                                                                 │
│  Entrypoint: main.py (root)                                    │
│  Protocol: HTTP + JWT Authorizer                               │
│  Role: ORCHESTRATOR (routes to specialist A2A agents)          │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ A2A Protocol (JSON-RPC 2.0)
                                  │ Auth: SigV4 (boto3 IAM)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SPECIALIST AGENTS (A2A Protocol)              │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  nexo_import    │  │  data_import    │  │   learning      │ │
│  │  (Smart HIL)    │  │  (Bulk Import)  │  │   (Memory)      │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │          │
│           ▼                    ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Gemini 3.0 Pro (with Thinking)                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────┘
                                  │ MCP Protocol
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AWS AURORA POSTGRESQL                       │
│                        (via MCP Gateway)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Runtime IDs

| Runtime | ID | Protocol | Purpose |
|---------|-----|----------|---------|
| HTTP Orchestrator | `faiston_asset_management-uSuLPsFQNH` | HTTP | Frontend entry point (JWT) |
| NEXO Import | `faiston_sga_nexo_import-0zNtFDAo7M` | A2A | Smart Import HIL |
| Data Import | `faiston_sga_import-sM56rCFLIr` | A2A | Bulk Import |
| Learning | `faiston_sga_learning-30cZIOFmzo` | A2A | Memory/Patterns |
| Validation | `faiston_sga_validation-3zgXMwCxGN` | A2A | Schema validation |

---

## Authentication by Layer

| Layer | Protocol | Auth Method |
|-------|----------|-------------|
| Frontend → Orchestrator | HTTP | JWT (Cognito) |
| Orchestrator → Agents | A2A (JSON-RPC) | SigV4 (IAM) |
| Agents → Database | MCP | SigV4 (IAM) |

### CRITICAL: Protocol Mismatch Error

**WRONG**: Frontend calling `faiston_sga_nexo_import` directly
- This runtime expects A2A protocol (SigV4)
- Frontend sends JWT
- Result: "Empty response payload" (auth mismatch)

**CORRECT**: Frontend calling `faiston_asset_management`
- This runtime accepts HTTP protocol (JWT)
- Routes internally via A2A to specialist agents
- Result: Proper response with HIL questions

### JWT Authorizer Configuration

> **CRITICAL**: JWT config MUST be in `.bedrock_agentcore.yaml`, NOT just workflow!

**Why:**
AgentCore deployments are **ASYNCHRONOUS**. When deploying:
1. CLI deploys agent → returns immediately
2. AWS processes async (~20 minutes)
3. Async completion **RESETS** config to YAML values

If JWT is only configured post-deploy, it gets overwritten.

**Config Location:** `/server/agentcore-inventory/.bedrock_agentcore.yaml`

```yaml
# In faiston_asset_management agent
authorizer_configuration:
  customJWTAuthorizer:
    discoveryUrl: https://cognito-idp.us-east-2.amazonaws.com/us-east-2_lkBXr4kjy/.well-known/openid-configuration
    allowedClients:
      - 7ovjm09dr94e52mpejvbu9v1cg
```

### Troubleshooting 403 Forbidden

**Symptom:** Frontend gets HTTP 403 when calling orchestrator.

**Check Runtime Config:**
```bash
AWS_PROFILE=faiston-aio python3 -c "
import boto3
session = boto3.Session(profile_name='faiston-aio')
client = session.client('bedrock-agentcore-control', region_name='us-east-2')
resp = client.get_agent_runtime(agentRuntimeId='faiston_asset_management-uSuLPsFQNH')
print(resp.get('authorizerConfiguration', {}))
"
```

**If Empty (`{}`)**: JWT authorizer missing. Check YAML and redeploy.

> **Full Documentation:** See `docs/AUTHENTICATION_ARCHITECTURE.md`

---

## Two Import Flows

### 1. NEXO Smart Import (AI-First)

Uses intelligent analysis with Gemini 3.0 Pro.

**Frontend Actions**:
- `nexo_analyze_file` → Analyze file structure, generate HIL questions
- `nexo_submit_answers` → Submit user answers, re-analyze
- `nexo_execute_import` → Execute import with confirmed mappings

**Agent**: `nexo_import`

**Flow**:
```
Upload → Analyze (Gemini) → HIL Questions → User Answers → Re-analyze → ... → Execute
```

### 2. Bulk Import (Simple)

Simple CSV/XLSX import with preview.

**Frontend Actions**:
- `preview_import` → Preview first N rows
- `execute_import` → Execute import with mapping

**Agent**: `data_import`

---

## Multi-Round HIL Dialogue (AGI-Like)

The NEXO agent implements iterative conversation with the user:

### Context Sent to Gemini (Every Round)

1. **File Content** — CSV/XLSX/PDF data
2. **Memory Context** — Prior learned patterns from LearningAgent
3. **Schema Context** — PostgreSQL target schema
4. **User Responses** — Accumulated answers from previous rounds
5. **User Comments** — Free-text instructions

### Round Progression

```
ROUND 1: Memory + File + Schema → Gemini → Questions → STOP
ROUND 2: Memory + File + Schema + Answers → Gemini → More Questions or Ready
ROUND N: All context → Gemini → Final Summary → STOP → User Approval → Execute
```

### Stop Conditions

Agent MUST stop and wait for user when:
- `hil_questions` generated (clarification needed)
- `confidence < 80%` on any column
- `unmapped_columns` detected
- Final approval required before import

The `stop_action: true` flag signals the Strands ReAct loop to pause.

---

## Code Locations

| Component | Path |
|-----------|------|
| Frontend Config | `client/lib/config/agentcore.ts` |
| Frontend Hook | `client/lib/hooks/useInventoryImport.ts` |
| Orchestrator | `server/agentcore-inventory/main.py` |
| A2A Client | `server/agentcore-inventory/shared/a2a_client.py` |
| NEXO Agent | `server/agentcore-inventory/agents/nexo_import/main.py` |
| File Analysis | `server/agentcore-inventory/agents/nexo_import/tools/analyze_file.py` |
| Gemini Analyzer | `server/agentcore-inventory/agents/nexo_import/tools/gemini_text_analyzer.py` |
| Audit Emitter | `server/agentcore-inventory/shared/audit_emitter.py` |

---

## Common Errors and Solutions

### 1. "Empty response payload from agent runtime"

**Cause**: Protocol mismatch (calling A2A agent with JWT)
**Solution**: Ensure frontend calls HTTP orchestrator, not A2A agent directly

### 2. Timeout during analysis

**Cause**: Gemini 3.0 Pro with Thinking can take 60-180s
**Solution**: A2A client timeout set to 300s

### 3. "Float types are not supported"

**Cause**: DynamoDB rejects Python float
**Solution**: Convert floats to Decimal in audit_emitter.py

### 4. Infinite analysis loop

**Cause**: ReAct framework auto-loops without stop signal
**Solution**: Return `stop_action: true` when HIL questions pending

### 5. "Falha na análise (sem detalhes)"

**Cause**: `gemini_text_analyzer.py` uses `google.genai.Client()` which expects `GOOGLE_API_KEY` env var. This env var is NOT set in AgentCore runtime because the API key is stored in SSM Parameter Store, not as an environment variable.

**Solution (BUG-010 FIX)**: Added SSM loading logic to `_get_genai_client()` in `tools/gemini_text_analyzer.py` to load the API key from `/faiston-one/academy/google-api-key` if not already in environment.

**Note**: The Strands Agent uses `LazyGeminiModel` which already had this SSM loading. The issue was that `gemini_text_analyzer.py` bypassed that and used a direct client.

---

## Change History

| Date | Change | Commit |
|------|--------|--------|
| 2026-01-13 | BUG-010: Added SSM loading to gemini_text_analyzer.py | pending |
| 2026-01-13 | Fixed protocol mismatch (reverted wrong runtime ID) | d9b3325 |
| 2026-01-13 | Added timeout 300s, Decimal conversion, stop_action | 6cdf86e |
| 2026-01-13 | Fixed S3 Unicode NFC normalization | 374be7b |
| 2026-01-12 | Implemented AGI-like multi-round HIL | cedb9c2 |

---

## MANDATORY Rules for Changes

1. **NEVER** change frontend to call A2A agents directly
2. **ALWAYS** route through HTTP orchestrator (faiston_asset_management)
3. **ALWAYS** return `stop_action: true` when HIL questions are pending
4. **ALWAYS** convert floats to Decimal before DynamoDB writes
5. **ALWAYS** use 300s timeout for Gemini Pro with Thinking calls
