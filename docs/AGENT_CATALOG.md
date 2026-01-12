# Agent Catalog - Faiston NEXO

Complete inventory of all AI agents in the Faiston NEXO platform.

## Table of Contents

1. [Overview](#1-overview)
2. [SGA Inventory Agents](#2-sga-inventory-agents)
3. [Academy Agents](#3-academy-agents)
4. [Portal Agents](#4-portal-agents)
5. [Agent Design Patterns](#5-agent-design-patterns)
6. [HIL Routing Rules](#6-hil-routing-rules)
7. [A2A Protocol Configuration](#7-a2a-protocol-configuration)

---

## 1. Overview

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Bedrock AgentCore                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Inventory     │  │    Academy      │  │     Portal      │ │
│  │   Runtime       │  │    Runtime      │  │     Runtime     │ │
│  │   (14 agents)   │  │   (6 agents)    │  │   (2 agents)    │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │          │
│           ▼                    ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │     AWS Strands Agents Framework + Google ADK v1.0      │   │
│  │              Gemini 3.0 Family (Pro + Flash)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Communication: A2A Protocol (JSON-RPC 2.0) on Port 9000       │
│  Memory: AgentCore Memory (STM + LTM + RAG)                    │
│  Discovery: SSM Parameter Store                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Runtime Summary

| Runtime | ID | Agents | Purpose |
|---------|-----|--------|---------|
| **Inventory** | `faiston_asset_management-uSuLPsFQNH` | 14 | SGA inventory management |
| **Academy** | `faiston_academy_agents-ODNvP6HxCD` | 6 | Learning platform |
| **Portal** | `faiston_portal_agents-PENDING` | 2 | Central orchestration |

### Agent Framework

All agents are built on **AWS Strands Agents Framework + Google ADK v1.0** with these base capabilities:

- **Framework**: AWS Strands Agents (open-source multi-agent orchestration)
- **Models**: Gemini 3.0 Pro (with Thinking) + Gemini 3.0 Flash
- **Memory**: AgentCore Memory (Session + STM + LTM + RAG)
- **Tools**: Custom function tools + MCP tools
- **Communication**: A2A Protocol (JSON-RPC 2.0)
- **Confidence Scoring**: 0.0-1.0 scale for HIL routing

### Model Configuration Summary

| Model | Thinking Mode | Use Case | Agent Count |
|-------|---------------|----------|-------------|
| **gemini-3.0-pro** | HIGH | Import/analysis agents with file reasoning | 5 |
| **gemini-3.0-pro** | None | Complex reasoning (compliance, audits) | 1 |
| **gemini-3.0-flash** | None | Operational agents (simple tasks) | 8 |

**Reference**: See [ADR-003: Gemini 3.0 Model Selection](./architecture/ADR-003-gemini-model-selection.md) for rationale.

---

## 2. SGA Inventory Agents

### Agent Summary Table

| # | Agent | Model | Thinking | Purpose | Path |
|---|-------|-------|----------|---------|------|
| 1 | EstoqueControlAgent | Flash | None | Main orchestrator for inventory | `dist/estoque_control/` |
| 2 | NexoImportAgent | **Pro** | **HIGH** | Smart import orchestrator | `dist/nexo_import/` |
| 3 | IntakeAgent | **Pro** | **HIGH** | NF-e XML processing | `dist/intake/` |
| 4 | ImportAgent | **Pro** | **HIGH** | Spreadsheet import (Excel/CSV) | `dist/import/` |
| 5 | LearningAgent | **Pro** | **HIGH** | Memory management and learning | `dist/learning/` |
| 6 | SchemaEvolutionAgent | **Pro** | **HIGH** | Dynamic schema evolution | `dist/schema_evolution/` |
| 7 | ValidationAgent | Flash | None | Data validation | `dist/validation/` |
| 8 | ComplianceAgent | **Pro** | None | Regulatory compliance | `dist/compliance/` |
| 9 | ReconciliacaoAgent | Flash | None | SAP reconciliation | `dist/reconciliacao/` |
| 10 | ObservationAgent | Flash | None | Field observations | `dist/observation/` |
| 11 | EquipmentResearchAgent | Flash | None | Equipment knowledge base | `dist/equipment_research/` |
| 12 | CarrierAgent | Flash | None | Carrier management | `dist/carrier/` |
| 13 | ExpeditionAgent | Flash | None | Expedition planning | `dist/expedition/` |
| 14 | ReverseAgent | Flash | None | Reverse logistics | `dist/reverse/` |

**Base Path**: `server/agentcore-inventory/dist/{agent_name}/`

---

### 2.1 EstoqueControlAgent (Main Orchestrator)

**Purpose**: Central orchestrator for all inventory operations.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/estoque_control/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `query_inventory`, `get_dashboard`, `search_assets` |
| **Tools** | `sga_list_inventory`, `sga_get_balance`, `sga_search_assets` |
| **Delegates To** | IntakeAgent, ImportAgent, ReconciliacaoAgent |

**Capabilities**:
- Natural language inventory queries
- Dashboard data aggregation
- Route requests to specialized agents
- Maintain conversation context

---

### 2.2 NexoImportAgent (Smart Import Orchestrator)

**Purpose**: AI-powered intelligent file import with learning.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/nexo_import/` |
| **Model** | **`gemini-3.0-pro`** |
| **Thinking** | **HIGH** (extended reasoning) |
| **Actions** | `smart_import`, `learn_from_import`, `analyze_file` |
| **Tools** | All import tools + `sga_learn_mapping` |
| **Confidence Threshold** | 0.80 |
| **A2A Delegates** | LearningAgent, SchemaEvolutionAgent |

**Capabilities**:
- Auto-detect file type (NF, Excel, CSV, images)
- Intelligent column mapping with schema understanding
- Learn from user corrections via LearningAgent
- Pre-flight schema validation
- Progressive confidence improvement
- Deep reasoning over file structure and patterns

**NEXO Import Flow**:
```
File Upload → OBSERVE → THINK → ASK → LEARN → ACT
                │                      │
                └── Confidence < 80% ──┴── HIL Review
```

**Architecture Pattern**:
- **OBSERVE**: Analyze file structure (delegate file analysis)
- **THINK**: Reason about mappings (Gemini 3.0 Pro with Thinking HIGH)
- **ASK**: Generate questions for HIL (recall memory first)
- **LEARN**: Delegate to LearningAgent via A2A (immediate + consolidation)
- **ACT**: Execute import with validated mappings

**Reference**:
- [NEXO Memory Architecture](./architecture/NEXO_MEMORY_ARCHITECTURE.md)
- [ADR-003: Gemini Model Selection](./architecture/ADR-003-gemini-model-selection.md)

---

### 2.3 IntakeAgent

**Purpose**: Process NF-e XML files for inventory intake.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/intake/` |
| **Model** | **`gemini-3.0-pro`** |
| **Thinking** | **HIGH** |
| **Actions** | `process_nf`, `validate_nf`, `extract_items` |
| **Tools** | `sga_create_movement`, `sga_validate_part_number`, `parse_nf`, `match_items` |
| **Confidence Threshold** | 0.80 |

**Capabilities**:
- Parse XML NF-e (Nota Fiscal Eletrônica)
- Extract line items with quantities using Vision
- Validate against part number catalog
- Create intake movements
- Deep reasoning over document structure

**Why Gemini 3.0 Pro + Thinking**: NF-e parsing requires complex document understanding, item extraction from semi-structured data, and validation against schemas.

---

### 2.4 ImportAgent

**Purpose**: Process spreadsheet imports (Excel, CSV).

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/import/` |
| **Model** | **`gemini-3.0-pro`** |
| **Thinking** | **HIGH** |
| **Actions** | `import_spreadsheet`, `validate_import`, `preview_import` |
| **Tools** | `sga_bulk_create_movements`, `sga_validate_bulk` |
| **Confidence Threshold** | 0.75 |

**Capabilities**:
- Parse Excel (.xlsx) and CSV files
- Map columns to inventory schema
- Validate data integrity
- Bulk movement creation
- Multi-sheet analysis

**Why Gemini 3.0 Pro + Thinking**: Spreadsheet imports require understanding file structure, column patterns, data types, and complex mapping to database schemas.

---

### 2.5 LearningAgent

**Purpose**: Continuous learning and memory management.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/learning/` |
| **Model** | **`gemini-3.0-pro`** |
| **Thinking** | **HIGH** |
| **Actions** | `learn`, `improve_model`, `update_mappings` |
| **Tools** | `create_episode_tool`, `retrieve_prior_knowledge_tool`, `generate_reflection_tool` |

**Capabilities**:
- User feedback processing
- Column mapping improvement
- Confidence calibration
- Pattern recognition
- Memory consolidation (STM → LTM)
- Self-managed memory strategy

**Memory Architecture**:
- **Session Memory**: Current interaction state (working memory)
- **Short-Term Memory (STM)**: Recent decisions (immediate storage)
- **Long-Term Memory (LTM)**: Learned patterns and schemas
- **Strategy**: Self-managed with custom consolidation

**Reference**:
- [NEXO Memory Architecture](./architecture/NEXO_MEMORY_ARCHITECTURE.md)
- [ADR-001: GLOBAL Namespace](./architecture/ADR-001-global-namespace.md)
- [ADR-002: Self-Managed Strategy](./architecture/ADR-002-self-managed-strategy.md)

---

### 2.6 SchemaEvolutionAgent

**Purpose**: Dynamic database schema evolution.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/schema_evolution/` |
| **Model** | **`gemini-3.0-pro`** |
| **Thinking** | **HIGH** |
| **Actions** | `create_column`, `modify_schema`, `validate_migration` |
| **Tools** | `generate_migration_sql`, `validate_schema_change`, `execute_ddl` |

**Capabilities**:
- Generate PostgreSQL DDL (ALTER TABLE)
- Validate schema changes for safety
- Execute migrations with rollback
- Track schema versions
- Reason about data types and constraints

**Why Gemini 3.0 Pro + Thinking**: Schema evolution requires deep reasoning about SQL, data types, constraints, and migration safety.

---

### 2.7 ValidationAgent

**Purpose**: Data validation and quality checks.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/validation/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `validate_data`, `check_constraints`, `verify_quality` |
| **Tools** | `validate_field`, `check_duplicates`, `verify_references` |

**Capabilities**:
- Field-level validation
- Constraint checking
- Duplicate detection
- Reference integrity verification

---

### 2.8 ComplianceAgent

**Purpose**: Regulatory compliance and audit checks.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/compliance/` |
| **Model** | **`gemini-3.0-pro`** |
| **Thinking** | None |
| **Actions** | `check_compliance`, `audit`, `validate_documentation` |
| **Tools** | `sga_audit_log`, `sga_compliance_rules` |

**Capabilities**:
- Regulatory compliance verification
- Audit trail generation
- Document validation
- Alert on violations

**Why Gemini 3.0 Pro (without Thinking)**: Compliance requires complex reasoning over regulations and audit rules, but not extended chain-of-thought.

---

### 2.9 ReconciliacaoAgent

**Purpose**: Inventory reconciliation and SAP comparison.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/reconciliacao/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `reconcile`, `compare_sap`, `generate_report` |
| **Tools** | `sga_reconcile_sap`, `sga_get_divergences` |
| **Confidence Threshold** | 0.85 |

**Capabilities**:
- Compare SGA with SAP exports
- Identify discrepancies
- Generate reconciliation reports
- Propose adjustments

---

### 2.10 ObservationAgent

**Purpose**: Field observations and anomaly detection.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/observation/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `record_observation`, `analyze_trend`, `flag_anomaly` |
| **Tools** | Image analysis, trend detection |

**Capabilities**:
- Field observation recording
- Photo/video analysis
- Trend identification
- Anomaly flagging

---

### 2.11 EquipmentResearchAgent

**Purpose**: Equipment knowledge base search.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/equipment_research/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `research_equipment`, `find_manual`, `get_specs` |
| **Tools** | Bedrock KB retrieval, S3 document search |

**Capabilities**:
- Equipment manual lookup
- Technical specifications
- Maintenance procedures
- Troubleshooting guides

---

### 2.12 CarrierAgent

**Purpose**: Carrier management for logistics.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/carrier/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `assign_carrier`, `track_shipment`, `rate_carriers` |
| **Tools** | Carrier APIs, tracking integration |

**Capabilities**:
- Carrier selection
- Shipment tracking
- Performance rating
- Cost optimization

---

### 2.13 ExpeditionAgent

**Purpose**: Expedition and dispatch planning.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/expedition/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `create_expedition`, `plan_route`, `optimize_load` |
| **Tools** | Route optimization, load planning |

**Capabilities**:
- Expedition creation
- Route optimization
- Load balancing
- Dispatch scheduling

---

### 2.14 ReverseAgent

**Purpose**: Reverse logistics and returns.

| Property | Value |
|----------|-------|
| **Path** | `server/agentcore-inventory/dist/reverse/` |
| **Model** | `gemini-3.0-flash` |
| **Thinking** | None |
| **Actions** | `process_return`, `inspect_return`, `restock` |
| **Tools** | Return processing, inspection checklists |

**Capabilities**:
- Return authorization
- Inspection workflow
- Restocking decisions
- Refurbishment routing

---

## 3. Academy Agents

### 3.1 LessonGeneratorAgent

**Purpose**: Generate lesson content from transcriptions.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-academy/agents/lesson_generator_agent.py` |
| **Actions** | `generate_lesson`, `create_outline`, `extract_key_points` |
| **Tools** | Content generation, outline creation |

### 3.2 QuizGeneratorAgent

**Purpose**: Create quizzes from lesson content.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-academy/agents/quiz_generator_agent.py` |
| **Actions** | `generate_quiz`, `create_questions`, `grade_answers` |
| **Tools** | Question generation, answer validation |

### 3.3 AudioGeneratorAgent

**Purpose**: Generate audio narration via ElevenLabs.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-academy/agents/audio_generator_agent.py` |
| **Actions** | `generate_audio`, `create_narration` |
| **Tools** | ElevenLabs TTS API |

### 3.4 SlideGeneratorAgent

**Purpose**: Create presentation slides.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-academy/agents/slide_generator_agent.py` |
| **Actions** | `generate_slides`, `create_deck` |
| **Tools** | Slide generation, template application |

### 3.5 VideoScriptAgent

**Purpose**: Generate video scripts.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-academy/agents/video_script_agent.py` |
| **Actions** | `generate_script`, `create_storyboard` |
| **Tools** | Script generation |

### 3.6 ClassroomOrchestratorAgent

**Purpose**: Orchestrate classroom experience.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-academy/agents/classroom_orchestrator_agent.py` |
| **Actions** | `start_lesson`, `next_section`, `handle_question` |
| **Tools** | Session management, progress tracking |

---

## 4. Portal Agents

### 4.1 NewsAgent

**Purpose**: Generate and curate news content.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-portal/agents/news_agent.py` |
| **Actions** | `generate_news`, `curate_feed`, `summarize_article` |
| **Tools** | Content generation, summarization |

### 4.2 NexoOrchestratorAgent

**Purpose**: Central NEXO AI copilot orchestration.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-portal/agents/nexo_orchestrator_agent.py` |
| **Actions** | `route_request`, `delegate`, `aggregate_response` |
| **Tools** | Agent routing, response aggregation |

**Capabilities**:
- Route requests to appropriate runtime
- Delegate to specialized agents
- Aggregate multi-agent responses
- Maintain cross-module context

---

## 5. Agent Design Patterns

### Base Agent Structure

```python
# Standard agent structure
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

class ExampleAgent(Agent):
    """Agent description."""

    name = "ExampleAgent"
    model = "gemini-3.0-pro"

    def __init__(self):
        super().__init__(
            name=self.name,
            model=self.model,
            instruction=self._get_system_prompt(),
            tools=self._get_tools(),
        )

    def _get_system_prompt(self) -> str:
        return """
        You are an expert in [domain].
        Your role is to [purpose].

        Guidelines:
        1. [Guideline 1]
        2. [Guideline 2]
        3. [Guideline 3]

        Always provide confidence scores for your outputs.
        """

    def _get_tools(self) -> list[FunctionTool]:
        # Lazy imports to avoid cold start timeout
        from ..tools import tool1, tool2
        return [tool1, tool2]
```

### Action Handler Pattern

```python
# main.py - Action handlers
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def agent_invocation(payload, context):
    """Entry point for A2A protocol invocations."""
    # Lazy import to meet 30s cold start limit
    from agents.example_agent import ExampleAgent

    agent = ExampleAgent()
    return agent.run(payload)
```

### Confidence Scoring Pattern

```python
# Tools should return confidence scores
def process_with_confidence(data: dict) -> dict:
    result = process_data(data)

    # Calculate confidence based on validation
    confidence = 1.0
    if missing_fields:
        confidence -= 0.2 * len(missing_fields)
    if ambiguous_mappings:
        confidence -= 0.1 * len(ambiguous_mappings)

    return {
        "result": result,
        "confidence": max(0.0, min(1.0, confidence)),
        "issues": missing_fields + ambiguous_mappings,
    }
```

---

## 6. HIL Routing Rules

### Confidence Thresholds

| Confidence | Action |
|------------|--------|
| ≥ 0.80 | **Autonomous** - Execute without approval |
| 0.60-0.79 | **Review** - Execute with notification |
| < 0.60 | **HIL Required** - Create approval task |

### HIL Task Types

| Type | Description | Assigned To |
|------|-------------|-------------|
| `approval` | Movement approval | Supervisor |
| `review` | Data review | Operator |
| `classification` | Ambiguous classification | Expert |
| `escalation` | Error resolution | Admin |

### HIL Task Flow

```
Agent Output
     │
     ▼
Confidence Score
     │
     ├── ≥ 0.80 ──────────► Execute
     │
     └── < 0.80 ──────────► Create HIL Task
                                  │
                                  ▼
                            DynamoDB: hil-tasks
                                  │
                                  ▼
                            Frontend: Task Inbox
                                  │
                                  ├── Approve ──► Execute
                                  │
                                  └── Reject ───► Log & Notify
```

### Creating HIL Tasks

```python
# Example HIL task creation
async def create_hil_task(
    task_type: str,
    payload: dict,
    confidence: float,
    assigned_to: str = None
) -> dict:
    task = {
        "task_id": str(uuid.uuid4()),
        "type": task_type,
        "status": "pending",
        "payload": payload,
        "confidence_score": confidence,
        "assigned_to": assigned_to or get_default_approver(task_type),
        "created_at": datetime.utcnow().isoformat(),
        "TTL": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
    }

    await dynamodb.put_item(
        TableName="faiston-one-sga-hil-tasks-prod",
        Item=task
    )

    return task
```

---

## 7. A2A Protocol Configuration

### Overview

All agents communicate using the **A2A (Agent-to-Agent) Protocol**, based on **JSON-RPC 2.0** specification.

| Property | Value |
|----------|-------|
| **Protocol** | JSON-RPC 2.0 |
| **Transport** | HTTP/HTTPS |
| **Port** | 9000 (default) |
| **Entry Point** | `@app.entrypoint` decorator in `main.py` |
| **Discovery** | AWS Systems Manager Parameter Store |
| **Authentication** | AWS IAM (cross-account role assumption) |

### A2A Message Format

```json
{
  "jsonrpc": "2.0",
  "method": "invoke_agent",
  "params": {
    "agent_id": "nexo_import",
    "action": "analyze_file",
    "payload": {
      "s3_key": "uploads/inventory.xlsx",
      "filename": "inventory.xlsx",
      "user_id": "user@example.com"
    }
  },
  "id": "req-123456"
}
```

### A2A Response Format

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "action": "analyze_file",
    "result": {
      "file_analysis": {...},
      "prior_knowledge": {...}
    },
    "agent_id": "nexo_import"
  },
  "id": "req-123456"
}
```

### Agent Discovery via SSM

Agent endpoints are registered in AWS Systems Manager Parameter Store:

```
/faiston-one/agents/nexo_import/endpoint
/faiston-one/agents/learning/endpoint
/faiston-one/agents/schema_evolution/endpoint
```

### Delegation Example

```python
from shared.a2a_client import delegate_to_learning

# Delegate to LearningAgent via A2A
response = await delegate_to_learning({
    "action": "retrieve_prior_knowledge",
    "user_id": "user@example.com",
    "filename": "inventory.xlsx",
    "file_analysis": file_analysis,
}, session_id=session_id)

if response.success:
    prior_knowledge = response.result
```

### Common A2A Patterns

| Source Agent | Target Agent | Action | Purpose |
|--------------|--------------|--------|---------|
| NexoImportAgent | LearningAgent | `retrieve_prior_knowledge` | Get learned mappings |
| NexoImportAgent | LearningAgent | `create_episode` | Store learning episode |
| NexoImportAgent | SchemaEvolutionAgent | `create_column` | Add database column |
| IntakeAgent | ValidationAgent | `validate_data` | Validate NF-e items |
| EstoqueControlAgent | ReconciliacaoAgent | `reconcile` | SAP comparison |

### References

- [AWS Strands Agents A2A Documentation](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/)
- [A2A Protocol Specification](https://aws.amazon.com/blogs/opensource/open-protocols-for-agent-interoperability-part-4-inter-agent-communication-on-a2a/)
- [Leveraging A2A with Strands](https://builder.aws.com/content/2y90GhUwgOEbKULKuehf2WHUf9Q/leveraging-agent-to-agent-a2a-with-strands-part-1)

---

## Related Documentation

- [SGA Estoque Architecture](./SGA_ESTOQUE_ARCHITECTURE.md)
- [NEXO Memory Architecture](./architecture/NEXO_MEMORY_ARCHITECTURE.md)
- [ADR-001: GLOBAL Namespace Design](./architecture/ADR-001-global-namespace.md)
- [ADR-002: Self-Managed Strategy Pattern](./architecture/ADR-002-self-managed-strategy.md)
- [ADR-003: Gemini 3.0 Model Selection](./architecture/ADR-003-gemini-model-selection.md)
- [AgentCore Implementation Guide](./AgentCore/IMPLEMENTATION_GUIDE.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Troubleshooting](./TROUBLESHOOTING.md)

---

**Last Updated:** January 2026
**Platform:** Faiston NEXO
**Total Agents:** 22 (14 Inventory + 6 Academy + 2 Portal)
**Framework:** AWS Strands Agents + Google ADK v1.0
**Models:** Gemini 3.0 Pro (with Thinking) + Gemini 3.0 Flash
