# PRD: Debug Agent

## Product Requirements Document

**Product Name:** Debug Agent (Intelligent Error Analysis)
**Version:** 1.0
**Created:** 2026-01-17
**Status:** Draft
**Product Owner:** Engineering Team

---

## 1. Executive Summary

### 1.1 Product Vision

Create an intelligent Debug Agent that transforms opaque error messages into actionable debugging insights. This AI-powered specialist will analyze errors from all inventory agents, research official documentation, identify root causes, and provide step-by-step debugging guidance—reducing mean-time-to-resolution by 50% for the engineering team.

### 1.2 Problem Statement

**Para:** Faiston Engineering Team (developers, DevOps, SREs)
**Que:** Struggle with opaque agent errors, spending excessive time tracing issues across 14+ specialist agents
**O:** Debug Agent
**É uma:** AI-powered error analysis specialist
**Que:** Provides intelligent analysis with root causes, documentation links, and debugging steps
**Diferentemente de:** Manual log inspection, generic error messages, or external debugging tools
**Nosso produto:** Integrates directly with the agent ecosystem, learns from patterns, and provides context-aware insights using real-time documentation research

### 1.3 Target Users

| Persona | Description | Primary Needs |
|---------|-------------|---------------|
| Backend Developer | Develops and maintains inventory agents | Quick root cause identification, code-level suggestions |
| DevOps Engineer | Manages AgentCore deployments | Infrastructure insights, AWS error correlation |
| QA Engineer | Tests agent workflows | Reproducible error scenarios, expected vs actual behavior |
| Frontend Developer | Integrates with agent APIs | Clear error messages for UI display, actionable user guidance |

---

## 2. Goals & Success Metrics

### 2.1 Business Goals

1. Reduce mean-time-to-resolution (MTTR) by 50%
2. Decrease escalations to senior engineers by 30%
3. Improve code quality through pattern-based learning
4. Build institutional knowledge of error patterns

### 2.2 User Goals

1. Understand error root cause within seconds, not hours
2. Get actionable debugging steps without context-switching
3. Access relevant documentation without manual searching
4. Learn from historical error resolutions

### 2.3 Key Performance Indicators (KPIs)

| KPI | Description | Target |
|-----|-------------|--------|
| Analysis Latency (Common) | Time to analyze known error patterns | < 5 seconds |
| Analysis Latency (Critical) | Time for novel/complex errors with deep research | < 30 seconds |
| Pattern Coverage | % of errors with recognized patterns | > 70% within 3 months |
| Resolution Rate | % of errors resolved using Debug Agent suggestions | > 60% |
| Developer Satisfaction | NPS score from engineering team | > 40 |

---

## 3. Functional Requirements

### 3.1 FR-1: Error Reception Interface

**Description:** Receive error payloads from all inventory agents via A2A Protocol.

**User Stories:**
- Como developer, quero que erros de qualquer agente sejam automaticamente enviados para análise para não precisar buscar logs manualmente

**Acceptance Criteria:**
- [ ] Accepts standardized error_context schema from all 14 specialists + orchestrator
- [ ] Validates incoming payload (error_type, operation, stack_trace, context)
- [ ] Returns acknowledgment within 100ms
- [ ] Handles concurrent error submissions (up to 50/second)

**Input Schema:**
```json
{
  "error_type": "string",
  "operation": "string",
  "message": "string",
  "stack_trace": "string | null",
  "context": {
    "agent_id": "string",
    "session_id": "string",
    "request_payload": "object",
    "timestamp": "ISO8601"
  },
  "recoverable": "boolean",
  "original_suggested_actions": ["string"]
}
```

### 3.2 FR-2: AI-Powered Analysis

**Description:** Use Gemini 2.5 Pro with Thinking for intelligent error analysis.

**User Stories:**
- Como developer, quero receber explicação técnica detalhada para entender a causa raiz do erro

**Acceptance Criteria:**
- [ ] Generates technical explanation in Portuguese (pt-BR)
- [ ] Identifies probable root causes (ranked by likelihood)
- [ ] Suggests debugging steps (ordered by effectiveness)
- [ ] Provides code-level suggestions when applicable
- [ ] Includes confidence level (high/medium/low) for each suggestion

**Output Schema:**
```json
{
  "analysis_id": "uuid",
  "original_error": { },
  "enriched_analysis": {
    "technical_explanation": "string (pt-BR)",
    "root_causes": [
      {
        "cause": "string",
        "likelihood": "high|medium|low",
        "evidence": "string"
      }
    ],
    "debugging_steps": [
      {
        "step": 1,
        "action": "string",
        "expected_result": "string"
      }
    ],
    "code_suggestions": [
      {
        "file": "string",
        "line": "number | null",
        "suggestion": "string"
      }
    ],
    "documentation_links": [
      {
        "title": "string",
        "url": "string",
        "relevance": "string"
      }
    ],
    "confidence_level": "high|medium|low",
    "analysis_time_ms": "number"
  }
}
```

### 3.3 FR-3: Documentation Research

**Description:** Research official documentation in real-time using MCP tools.

**User Stories:**
- Como developer, quero links para documentação oficial relevante para aprofundar meu entendimento

**Acceptance Criteria:**
- [ ] Searches AWS documentation (AgentCore, Bedrock, Lambda, Aurora)
- [ ] Searches Strands Agents SDK documentation
- [ ] Searches Gemini API documentation
- [ ] Searches Context7 for library-specific issues
- [ ] Returns direct links to relevant documentation sections
- [ ] Caches common documentation queries (5-minute TTL)

**MCP Tools Used:**
- `mcp__aws-documentation-mcp-server__search_documentation`
- `mcp__aws-documentation-mcp-server__read_documentation`
- `mcp__bedrock-agentcore-mcp-server__search_agentcore_docs`
- `mcp__context7__query-docs` (for Strands, Python libraries)

### 3.4 FR-4: Pattern Learning

**Description:** Store and retrieve error patterns using AgentCore Memory.

**User Stories:**
- Como developer, quero que o sistema aprenda com erros passados para dar respostas mais rápidas e precisas

**Acceptance Criteria:**
- [ ] Stores successful resolutions in LTM (Long-Term Memory)
- [ ] Retrieves similar past errors before LLM analysis
- [ ] Updates pattern confidence based on developer feedback
- [ ] Memory namespace: `/strategy/debug/error_patterns`
- [ ] TTL: 90 days for patterns, indefinite for confirmed fixes

**Memory Schema:**
```json
{
  "pattern_id": "string",
  "error_signature": "string (hash of type+operation+key_context)",
  "occurrences": "number",
  "successful_resolution": {
    "root_cause": "string",
    "fix_applied": "string",
    "resolved_by": "string",
    "resolved_at": "ISO8601"
  },
  "confidence": "number (0-1)",
  "last_seen": "ISO8601"
}
```

### 3.5 FR-5: Error Propagation

**Description:** Return enriched error to calling agent and propagate to frontend.

**User Stories:**
- Como developer, quero ver o erro enriquecido no console do browser para debugar sem abrir logs

**Acceptance Criteria:**
- [ ] Returns enriched analysis to calling agent
- [ ] Agent logs enriched error with `[DEBUG-AGENT]` prefix
- [ ] Error reaches frontend via existing error propagation (HTTP 4xx/5xx)
- [ ] Frontend displays human-readable analysis in browser console
- [ ] Frontend can optionally render analysis in error modal

**Frontend Integration:**
```typescript
// agentcoreBase.ts - Error handling enhancement
interface EnrichedError extends Error {
  debugAnalysis?: {
    technicalExplanation: string;
    rootCauses: Array<{ cause: string; likelihood: string }>;
    debuggingSteps: Array<{ step: number; action: string }>;
    documentationLinks: Array<{ title: string; url: string }>;
  };
}
```

### 3.6 FR-6: Circuit Breaker & Self-Protection

**Description:** Prevent cascade failures and protect system stability.

**User Stories:**
- Como DevOps, quero que o Debug Agent não degrade a performance do sistema em caso de sobrecarga

**Acceptance Criteria:**
- [ ] Circuit breaker: 3 failures → OPEN state (60s reset)
- [ ] Timeout: 30s max for analysis (graceful degradation after 5s)
- [ ] Rate limiting: 100 requests/minute per agent
- [ ] Fallback: Returns original error if Debug Agent unavailable
- [ ] Health check endpoint: `/health` returns circuit state

---

## 4. Technical Architecture

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEBUG AGENT FLOW                                     │
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐ │
│  │ Any Specialist│────▶│ DebugHook    │────▶│     Debug Agent              │ │
│  │ Agent (error) │     │ (intercept)  │     │  (A2A Specialist)            │ │
│  └──────────────┘     └──────────────┘     │                              │ │
│                                             │  Model: Gemini 2.5 Pro       │ │
│                                             │  + Thinking Enabled          │ │
│                                             │                              │ │
│                                             │  Tools:                      │ │
│                                             │  - analyze_error             │ │
│                                             │  - search_documentation      │ │
│                                             │  - query_memory_patterns     │ │
│                                             │  - store_resolution          │ │
│                                             └──────────────┬───────────────┘ │
│                                                            │                 │
│                              ┌─────────────────────────────┼───────────────┐ │
│                              │                             │               │ │
│                              ▼                             ▼               │ │
│  ┌──────────────────────────────┐     ┌──────────────────────────────────┐ │
│  │     AgentCore Memory         │     │   MCP Gateway (Documentation)    │ │
│  │  /strategy/debug/patterns    │     │   - AWS Docs                     │ │
│  │                              │     │   - AgentCore Docs               │ │
│  │  STM: Current session errors │     │   - Context7 (Strands, libs)     │ │
│  │  LTM: Resolved patterns      │     └──────────────────────────────────┘ │
│  └──────────────────────────────┘                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent Framework | AWS Strands Agents | Agent implementation |
| Agent Runtime | AWS Bedrock AgentCore | Deployment & scaling |
| LLM | Gemini 2.5 Pro + Thinking | Error analysis reasoning |
| Memory | AgentCore Memory (STM/LTM) | Pattern storage |
| Documentation | MCP Gateway | Real-time doc research |
| Protocol | A2A (JSON-RPC 2.0) | Inter-agent communication |
| Auth | SigV4 (IAM) | Agent-to-agent auth |

### 4.3 Integration Pattern: DebugHook

```python
# shared/hooks/debug_hook.py
from strands.hooks import HookProvider
from shared.a2a_client import A2AClient

class DebugHook(HookProvider):
    """Intercepts errors and sends to Debug Agent for analysis."""

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout = timeout_seconds
        self.client = A2AClient()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            reset_timeout=60
        )

    async def on_error(self, error: Exception, context: dict) -> dict:
        """Called when any agent encounters an error."""
        if self.circuit_breaker.is_open:
            return {"enriched": False, "reason": "circuit_open"}

        try:
            analysis = await asyncio.wait_for(
                self.client.invoke_agent(
                    agent_id="debug",
                    payload={
                        "error_type": type(error).__name__,
                        "message": str(error),
                        "context": context
                    }
                ),
                timeout=self.timeout
            )
            return {"enriched": True, "analysis": analysis}
        except asyncio.TimeoutError:
            return {"enriched": False, "reason": "timeout"}
        except Exception as e:
            self.circuit_breaker.record_failure()
            return {"enriched": False, "reason": str(e)}
```

### 4.4 Agent Configuration

```yaml
# .bedrock_agentcore.yaml (debug agent)
agents:
  - name: faiston_sga_debug
    description: "Intelligent error analysis agent for inventory system"
    protocol: a2a  # Internal only, not HTTP
    model: gemini-2.5-pro
    thinking_enabled: true
    memory:
      namespace: /strategy/debug/error_patterns
      ttl_days: 90
    tools:
      - analyze_error
      - search_documentation
      - query_memory_patterns
      - store_resolution
    rate_limit:
      requests_per_minute: 100
    timeout_seconds: 30
```

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Analysis latency (cached pattern) | < 2s | P95 |
| Analysis latency (common error) | < 5s | P95 |
| Analysis latency (novel error + research) | < 30s | P95 |
| Throughput | 100 req/min | Per agent source |
| Memory query latency | < 500ms | P99 |

### 5.2 Availability

| Metric | Target |
|--------|--------|
| Uptime | 99.5% |
| Graceful degradation | 100% (fallback to original error) |
| Recovery time | < 60s (circuit breaker reset) |

### 5.3 Security

| Requirement | Implementation |
|-------------|----------------|
| Authentication | SigV4 (IAM) for A2A calls |
| Authorization | IAM policies per agent |
| Data encryption | TLS 1.3 in transit, AES-256 at rest |
| PII handling | No PII stored in error patterns |
| Audit logging | All analyses logged to CloudWatch |

### 5.4 Observability

| Component | Tool | Metrics |
|-----------|------|---------|
| Logs | CloudWatch Logs | All analysis requests/responses |
| Metrics | CloudWatch Metrics | Latency, error rate, pattern hits |
| Traces | X-Ray | End-to-end request tracing |
| Dashboards | CloudWatch Dashboards | Real-time debug agent health |

---

## 6. Deployment & CI/CD

### 6.1 Deployment Pipeline

```
GitHub Push → GitHub Actions → Terraform Plan → Review → Terraform Apply → AgentCore Deploy
```

### 6.2 Environment Strategy

| Environment | Purpose | AgentCore Runtime |
|-------------|---------|------------------|
| Development | Local testing | Local (not deployed) |
| Staging | Integration testing | faiston_sga_debug-staging-* |
| Production | Live system | faiston_sga_debug-* |

---

## 7. Roadmap

### Phase 1: MVP (Week 1-2)
- [ ] Basic Debug Agent with error reception
- [ ] Gemini 2.5 Pro analysis (no thinking)
- [ ] Return enriched error to calling agent
- [ ] CloudWatch logging

### Phase 2: Intelligence (Week 3-4)
- [ ] Enable Thinking mode for complex errors
- [ ] MCP documentation research integration
- [ ] AgentCore Memory pattern storage
- [ ] Circuit breaker implementation

### Phase 3: Learning (Week 5-6)
- [ ] Pattern matching from historical errors
- [ ] Developer feedback loop (thumbs up/down)
- [ ] Confidence scoring refinement
- [ ] Dashboard with top error patterns

### Phase 4: Frontend Integration (Week 7-8)
- [ ] Frontend error modal with debug analysis
- [ ] Browser console rich formatting
- [ ] Copy-to-clipboard for debugging steps
- [ ] Link to relevant documentation

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Analysis adds latency to error responses | Medium | High | Async invocation with 5s timeout fallback |
| LLM hallucination in suggestions | High | Medium | Confidence levels, documentation links, human review |
| Cascade failures from Debug Agent issues | High | Low | Circuit breaker (3 failures → open) |
| Memory storage costs | Low | Medium | 90-day TTL, pattern deduplication |
| Documentation API rate limits | Medium | Medium | Caching (5-min TTL), graceful degradation |

---

## 9. Integration Tasks (Existing Agents)

### 9.1 DebugHook Integration

Add DebugHook to all specialist agents:

```python
# Each specialist main.py
from shared.hooks.debug_hook import DebugHook

agent = Agent(
    name="faiston_sga_*",
    hooks=[
        LoggingHook(),
        MetricsHook(),
        DebugHook(timeout_seconds=5.0),  # NEW
    ],
    ...
)
```

### 9.2 Affected Files

| File | Change |
|------|--------|
| `server/agentcore-inventory/agents/orchestrators/estoque/main.py` | Add DebugHook |
| `server/agentcore-inventory/agents/specialists/*/main.py` | Add DebugHook (14 files) |
| `server/agentcore-inventory/shared/hooks/__init__.py` | Export DebugHook |
| `client/lib/services/agentcoreBase.ts` | Handle enriched error display |
| `terraform/modules/agentcore/main.tf` | Add debug agent resource |

---

## 10. Appendix

### A. Error Classification

| Error Type | LLM Model | Research Depth |
|------------|-----------|----------------|
| Validation Error | Flash | None (pattern match) |
| Network Timeout | Flash | AWS docs only |
| Database Error | Pro | Aurora + AgentCore docs |
| LLM Error | Pro + Thinking | Gemini + Strands docs |
| Unknown | Pro + Thinking | Full research |

### B. Sample Enriched Error

```json
{
  "analysis_id": "dbg-20260117-abc123",
  "original_error": {
    "error_type": "TimeoutError",
    "operation": "invoke_specialist",
    "message": "A2A call to nexo_import timed out after 300s"
  },
  "enriched_analysis": {
    "technical_explanation": "O agente nexo_import excedeu o timeout de 300 segundos durante análise de arquivo. Isso geralmente ocorre quando o Gemini Pro com Thinking está processando arquivos grandes (>10MB) ou com muitas colunas ambíguas.",
    "root_causes": [
      {
        "cause": "Arquivo de entrada muito grande para análise em tempo real",
        "likelihood": "high",
        "evidence": "Timeout ocorreu em invoke_specialist, indicando processamento prolongado"
      },
      {
        "cause": "Gemini Thinking travou em loop de raciocínio",
        "likelihood": "medium",
        "evidence": "Thinking mode pode entrar em loops com prompts ambíguos"
      }
    ],
    "debugging_steps": [
      {
        "step": 1,
        "action": "Verificar tamanho do arquivo de entrada no S3",
        "expected_result": "Arquivo > 10MB indica necessidade de chunking"
      },
      {
        "step": 2,
        "action": "Checar CloudWatch Logs do nexo_import",
        "expected_result": "Log mostrará onde o processamento parou"
      },
      {
        "step": 3,
        "action": "Testar com arquivo menor (< 1MB)",
        "expected_result": "Se funcionar, problema é tamanho do arquivo"
      }
    ],
    "documentation_links": [
      {
        "title": "Gemini File API Limits",
        "url": "https://ai.google.dev/gemini-api/docs/files#file-limits",
        "relevance": "Limites de tamanho de arquivo para API Gemini"
      },
      {
        "title": "AgentCore Timeout Configuration",
        "url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-configuration.html",
        "relevance": "Como configurar timeouts em AgentCore"
      }
    ],
    "confidence_level": "high",
    "analysis_time_ms": 2340
  }
}
```

### C. Scope Limitations

This Debug Agent is scoped **ONLY** to the Inventory Project (SGA):

- **Included**: All 14 specialist agents + 1 orchestrator in `server/agentcore-inventory/`
- **Excluded**: Other Faiston projects (Academy, Portal, etc.)
- **Future Expansion**: After successful validation, may extend to other projects

---

**Document Status:** Draft
**Next Review:** 2026-01-24
**Approval Required:** Engineering Lead, Product Owner
