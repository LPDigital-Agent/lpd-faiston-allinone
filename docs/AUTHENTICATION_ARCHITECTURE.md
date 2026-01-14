# Faiston One Authentication Architecture

> **Last Updated:** 2026-01-14
> **Status:** Production
> **Architecture:** Strands Orchestrator Agent (LLM-based routing)

This document describes the authentication architecture for Faiston One platform, specifically for the AgentCore multi-agent system.

> **REFACTORED (2026-01-14):** The orchestrator was transformed from a 4,426-line monolith with 75 handlers to a ~490-line **Strands Agent** with LLM-based routing via Gemini Flash.

---

## Overview

The platform uses a **dual authentication model**:

| Flow | Auth Type | Use Case |
|------|-----------|----------|
| Frontend → AgentCore | **JWT Bearer Token** (Cognito) | External/user-facing requests |
| AgentCore → AgentCore | **IAM SigV4** (A2A) | Internal agent-to-agent communication |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOW                                      │
│                                                                             │
│   Frontend (React)                                                          │
│         │                                                                   │
│         │ JWT Bearer Token (Cognito accessToken)                            │
│         ▼                                                                   │
│   faiston_asset_management (HTTP runtime, JWT Authorizer)                   │
│         │                                                                   │
│         │ IAM SigV4 (A2A Protocol)                                          │
│         ▼                                                                   │
│   faiston_sga_* Specialist Agents (A2A runtimes)                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cognito Configuration

### User Pool

| Property | Value |
|----------|-------|
| Pool ID | `us-east-2_lkBXr4kjy` |
| Client ID | `7ovjm09dr94e52mpejvbu9v1cg` |
| Region | `us-east-2` |
| Discovery URL | `https://cognito-idp.us-east-2.amazonaws.com/us-east-2_lkBXr4kjy/.well-known/openid-configuration` |

### Token Usage

- **Frontend uses:** `accessToken` (NOT `idToken`)
- **Token refresh:** Handled by `ensureValidAccessToken()` in `client/services/authStore.ts`
- **Token header:** `Authorization: Bearer <accessToken>`

---

## AgentCore Runtime Types

### Orchestrator (HTTP Protocol + Strands Agent)

| Property | Value |
|----------|-------|
| Runtime Name | `faiston_asset_management` |
| Runtime ID | `faiston_asset_management-uSuLPsFQNH` |
| Protocol | `HTTP` |
| Auth | JWT Bearer Token |
| Use Case | Frontend-facing entry point |
| Architecture | **Strands Agent** with LLM-based routing |
| Model | Gemini 2.5 Flash (for fast routing decisions) |
| Code Size | ~490 lines (refactored from 4,426 lines) |

**Routing Pattern:**
```
Frontend → HTTP /invocations → Strands Agent (Gemini) → invoke_specialist tool → A2A Protocol → Specialist
```

The orchestrator uses a **Strands `Agent`** object with a system prompt that describes all 14 specialist agents. The LLM decides which specialist to invoke based on user intent.

### Specialist Agents (A2A Protocol)

| Runtime Name | Protocol | Auth | Use Case |
|--------------|----------|------|----------|
| `faiston_sga_nexo_import` | A2A | SigV4 | Intelligent file import orchestrator |
| `faiston_sga_learning` | A2A | SigV4 | Episodic memory and pattern learning |
| `faiston_sga_validation` | A2A | SigV4 | Schema and data validation |
| `faiston_sga_schema_evolution` | A2A | SigV4 | Dynamic schema evolution |
| `faiston_sga_intake` | A2A | SigV4 | NF reader (PDF/XML) |
| `faiston_sga_import` | A2A | SigV4 | Bulk import (spreadsheets, CSV) |
| `faiston_sga_estoque_control` | A2A | SigV4 | Inventory control and balance |
| `faiston_sga_compliance` | A2A | SigV4 | Regulatory compliance and audit |
| `faiston_sga_reconciliacao` | A2A | SigV4 | SAP reconciliation |
| `faiston_sga_expedition` | A2A | SigV4 | Shipment management |
| `faiston_sga_carrier` | A2A | SigV4 | Carrier management and tracking |
| `faiston_sga_reverse` | A2A | SigV4 | Reverse logistics |
| `faiston_sga_observation` | A2A | SigV4 | Monitoring and alerting |
| `faiston_sga_equipment_research` | A2A | SigV4 | Equipment KB and research |

---

## Configuration Location

### JWT Authorizer (PRIMARY)

**File:** `/server/agentcore-inventory/.bedrock_agentcore.yaml`

```yaml
# In faiston_asset_management agent config
authorizer_configuration:
  customJWTAuthorizer:
    discoveryUrl: https://cognito-idp.us-east-2.amazonaws.com/us-east-2_lkBXr4kjy/.well-known/openid-configuration
    allowedClients:
      - 7ovjm09dr94e52mpejvbu9v1cg
```

### CRITICAL: Why Config MUST Be in YAML

AgentCore deployments are **ASYNCHRONOUS**:

1. AgentCore CLI deploys agent → returns immediately
2. AWS continues processing async (~20 minutes)
3. Async completion **RESETS** config to what's in YAML file

**PROBLEM:** If JWT config is only added post-deploy (via workflow), AWS async completion will overwrite it with `null`.

**SOLUTION:** JWT authorizer config MUST be in `.bedrock_agentcore.yaml` so it's included during deployment.

---

## Common Issues & Troubleshooting

### HTTP 403 Forbidden

**Symptom:** Frontend receives `403` when calling AgentCore orchestrator.

**Cause:** JWT authorizer is not configured on the runtime.

**How to Check:**
```bash
AWS_PROFILE=faiston-aio python3 -c "
import boto3
session = boto3.Session(profile_name='faiston-aio')
client = session.client('bedrock-agentcore-control', region_name='us-east-2')
resp = client.get_agent_runtime(agentRuntimeId='faiston_asset_management-uSuLPsFQNH')
print(resp.get('authorizerConfiguration', {}))
"
```

**Expected Output:**
```python
{'customJWTAuthorizer': {'discoveryUrl': 'https://cognito-idp.us-east-2.amazonaws.com/us-east-2_lkBXr4kjy/.well-known/openid-configuration', 'allowedClients': ['7ovjm09dr94e52mpejvbu9v1cg']}}
```

**If Empty (`{}`):** The JWT authorizer is not configured. Check `.bedrock_agentcore.yaml` and redeploy.

### Empty Response Payload

**Symptom:** AgentCore returns empty response when calling specialist agents directly.

**Cause:** Calling an A2A agent (SigV4 auth) with a JWT token.

**Solution:** Frontend MUST call the HTTP orchestrator (`faiston_asset_management`), NOT specialist agents directly.

```
❌ Frontend → faiston_sga_nexo_import (A2A) → Empty response
✅ Frontend → faiston_asset_management (HTTP) → faiston_sga_nexo_import (A2A)
```

### Token Expired

**Symptom:** Intermittent 401/403 errors during long-running operations.

**Cause:** JWT token expired during the operation.

**Solution:** Frontend uses `ensureValidAccessToken()` which automatically refreshes tokens before expiration.

---

## AWS Documentation References

- [AgentCore Runtime Authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-authentication.html)
- [AgentCore A2A Protocol](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html)
- [Custom JWT Authorizer](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-jwt-authorizer.html)

---

## Architecture Decision Records

### ADR-001: Dual Authentication Model

**Decision:** Use JWT for external (frontend) access and SigV4 for internal (A2A) communication.

**Rationale:**
- JWT provides user identity for audit trails
- SigV4 provides secure service-to-service communication
- AWS AgentCore does NOT support both auth types on a single runtime

### ADR-002: JWT Config in YAML

**Decision:** Place JWT authorizer config in `.bedrock_agentcore.yaml` instead of post-deploy workflow.

**Rationale:**
- AgentCore async deployment resets config to YAML values
- Post-deploy configuration is not persistent
- YAML config is version-controlled and auditable

---

## Related Documentation

- [SMART_IMPORT_ARCHITECTURE.md](./SMART_IMPORT_ARCHITECTURE.md) - Import flow architecture
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [Deploy Workflow](.github/workflows/deploy-agentcore-inventory.yml) - Deployment process
