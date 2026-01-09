# Agent Catalog - Faiston NEXO

Complete inventory of all AI agents in the Faiston NEXO platform.

## Table of Contents

1. [Overview](#1-overview)
2. [SGA Inventory Agents](#2-sga-inventory-agents)
3. [Academy Agents](#3-academy-agents)
4. [Portal Agents](#4-portal-agents)
5. [Agent Design Patterns](#5-agent-design-patterns)
6. [HIL Routing Rules](#6-hil-routing-rules)

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
│  │                   Google ADK Framework                   │   │
│  │                   + Gemini 3.0 Pro LLM                   │   │
│  └─────────────────────────────────────────────────────────┘   │
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

All agents are built on Google ADK with these base capabilities:

- **Model**: Gemini 3.0 Pro (via LiteLLM)
- **Memory**: AgentCore Session Memory
- **Tools**: Custom function tools + MCP tools
- **Confidence Scoring**: 0.0-1.0 scale for HIL routing

---

## 2. SGA Inventory Agents

### 2.1 EstoqueControlAgent (Main Orchestrator)

**Purpose**: Central orchestrator for all inventory operations.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/estoque_control_agent.py` |
| **Actions** | `query_inventory`, `get_dashboard`, `search_assets` |
| **Tools** | `sga_list_inventory`, `sga_get_balance`, `sga_search_assets` |
| **Delegates To** | IntakeAgent, ImportAgent, ReconciliacaoAgent |

**Capabilities**:
- Natural language inventory queries
- Dashboard data aggregation
- Route requests to specialized agents
- Maintain conversation context

### 2.2 IntakeAgent

**Purpose**: Process NF-e XML files for inventory intake.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/intake_agent.py` |
| **Actions** | `process_nf`, `validate_nf`, `extract_items` |
| **Tools** | `sga_create_movement`, `sga_validate_part_number` |
| **Confidence Threshold** | 0.80 |

**Capabilities**:
- Parse XML NF-e (Nota Fiscal Eletrônica)
- Extract line items with quantities
- Validate against part number catalog
- Create intake movements

### 2.3 ImportAgent

**Purpose**: Process spreadsheet imports (Excel, CSV).

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/import_agent.py` |
| **Actions** | `import_spreadsheet`, `validate_import`, `preview_import` |
| **Tools** | `sga_bulk_create_movements`, `sga_validate_bulk` |
| **Confidence Threshold** | 0.75 |

**Capabilities**:
- Parse Excel (.xlsx) and CSV files
- Map columns to inventory schema
- Validate data integrity
- Bulk movement creation

### 2.4 NexoImportAgent (Smart Import)

**Purpose**: AI-powered intelligent file import with learning.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/nexo_import_agent.py` |
| **Actions** | `smart_import`, `learn_from_import`, `analyze_file` |
| **Tools** | All import tools + `sga_learn_mapping` |
| **Confidence Threshold** | 0.80 |

**Capabilities**:
- Auto-detect file type (NF, Excel, CSV)
- Intelligent column mapping
- Learn from user corrections
- Pre-flight schema validation
- Progressive confidence improvement

**NEXO Import Flow**:
```
File Upload → Analyze → Questions → Validate → Process → Learn
                │                      │
                └── Confidence < 80% ──┴── HIL Review
```

### 2.5 ReconciliacaoAgent

**Purpose**: Inventory reconciliation and SAP comparison.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/reconciliacao_agent.py` |
| **Actions** | `reconcile`, `compare_sap`, `generate_report` |
| **Tools** | `sga_reconcile_sap`, `sga_get_divergences` |
| **Confidence Threshold** | 0.85 |

**Capabilities**:
- Compare SGA with SAP exports
- Identify discrepancies
- Generate reconciliation reports
- Propose adjustments

### 2.6 ComplianceAgent

**Purpose**: Regulatory compliance and audit checks.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/compliance_agent.py` |
| **Actions** | `check_compliance`, `audit`, `validate_documentation` |
| **Tools** | `sga_audit_log`, `sga_compliance_rules` |

**Capabilities**:
- Regulatory compliance verification
- Audit trail generation
- Document validation
- Alert on violations

### 2.7 ComunicacaoAgent

**Purpose**: Notifications and alerts.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/comunicacao_agent.py` |
| **Actions** | `notify`, `alert`, `send_report` |
| **Tools** | Email integration, Slack webhooks |

**Capabilities**:
- Low stock alerts
- Approval notifications
- Report distribution
- Escalation handling

### 2.8 CarrierAgent

**Purpose**: Carrier management for logistics.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/carrier_agent.py` |
| **Actions** | `assign_carrier`, `track_shipment`, `rate_carriers` |
| **Tools** | Carrier APIs, tracking integration |

**Capabilities**:
- Carrier selection
- Shipment tracking
- Performance rating
- Cost optimization

### 2.9 ExpeditionAgent

**Purpose**: Expedition and dispatch planning.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/expedition_agent.py` |
| **Actions** | `create_expedition`, `plan_route`, `optimize_load` |
| **Tools** | Route optimization, load planning |

**Capabilities**:
- Expedition creation
- Route optimization
- Load balancing
- Dispatch scheduling

### 2.10 ReverseAgent

**Purpose**: Reverse logistics and returns.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/reverse_agent.py` |
| **Actions** | `process_return`, `inspect_return`, `restock` |
| **Tools** | Return processing, inspection checklists |

**Capabilities**:
- Return authorization
- Inspection workflow
- Restocking decisions
- Refurbishment routing

### 2.11 ObservationAgent

**Purpose**: Field observations and anomaly detection.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/observation_agent.py` |
| **Actions** | `record_observation`, `analyze_trend`, `flag_anomaly` |
| **Tools** | Image analysis, trend detection |

**Capabilities**:
- Field observation recording
- Photo/video analysis
- Trend identification
- Anomaly flagging

### 2.12 EquipmentResearchAgent

**Purpose**: Equipment knowledge base search.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/equipment_research_agent.py` |
| **Actions** | `research_equipment`, `find_manual`, `get_specs` |
| **Tools** | Bedrock KB retrieval, S3 document search |

**Capabilities**:
- Equipment manual lookup
- Technical specifications
- Maintenance procedures
- Troubleshooting guides

### 2.13 LearningAgent

**Purpose**: Continuous learning and model improvement.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/learning_agent.py` |
| **Actions** | `learn`, `improve_model`, `update_mappings` |
| **Tools** | Feedback collection, model tuning |

**Capabilities**:
- User feedback processing
- Column mapping improvement
- Confidence calibration
- Pattern recognition

### 2.14 InventoryCountAgent

**Purpose**: Physical inventory counting.

| Property | Value |
|----------|-------|
| **File** | `server/agentcore-inventory/agents/inventory_count_agent.py` |
| **Actions** | `count_inventory`, `adjust_stock`, `generate_count_sheet` |
| **Tools** | Count sheet generation, adjustment creation |

**Capabilities**:
- Count sheet generation
- Discrepancy identification
- Adjustment proposals
- Count verification

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

@app.action("example_action")
async def handle_example_action(request):
    # Lazy import to meet 30s cold start limit
    from agents.example_agent import ExampleAgent

    agent = ExampleAgent()
    return await agent.run(request.payload)
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

## Related Documentation

- [AgentCore Implementation Guide](AgentCore/IMPLEMENTATION_GUIDE.md)
- [SGA Architecture](architecture/SGA_ESTOQUE_ARCHITECTURE.md)
- [Database Schema](DATABASE_SCHEMA.md)
- [Troubleshooting](TROUBLESHOOTING.md)

---

**Last Updated:** January 2026
**Platform:** Faiston NEXO
**Total Agents:** 22
