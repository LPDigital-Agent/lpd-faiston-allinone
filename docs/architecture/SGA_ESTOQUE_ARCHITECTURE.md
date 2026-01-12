# SGA Inventory Module Architecture - Faiston NEXO

## Overview

The **SGA Inventory** module (Asset Management System - Inventory) is a complete inventory management system with AI capabilities, human-in-the-loop (HIL) approval workflows, and offline/PWA support.

**Technology Stack:**
- **Framework:** AWS Strands Agents Framework + Google ADK v1.0
- **Models:** Gemini 3.0 Pro (with Thinking) + Gemini 3.0 Flash
- **Memory:** AgentCore Memory (Session + STM + LTM + RAG)
- **Communication:** A2A Protocol (JSON-RPC 2.0) on Port 9000
- **Primary Datastore:** Aurora PostgreSQL (inventory data)
- **Secondary Datastore:** DynamoDB (HIL tasks, audit logs, sessions)

---

## 1. High-Level Architecture

```mermaid
flowchart TB
    subgraph "Frontend - Next.js 16"
        CF[CloudFront CDN]
        S3F[S3 Frontend Bucket]
        URLRw[URL Rewriter Function]
    end

    subgraph "React Client"
        Pages[25+ Pages/Routes]
        Contexts[6 Contexts]
        Hooks[29 Hooks]
        Services[sgaAgentcore.ts]
    end

    subgraph "AWS Bedrock AgentCore Runtime"
        Runtime[AgentCore Runtime\nfaiston_asset_management-uSuLPsFQNH]
        Memory[AgentCore Memory\nSession + STM + LTM + RAG]
        A2A[A2A Protocol\nJSON-RPC 2.0:9000]

        subgraph "AWS Strands Agents (14 Agents)"
            EstoqueCtrl[EstoqueControl Agent]
            Intake[Intake Agent]
            Import[Import Agent]
            NexoImport[NexoImport Agent]
            Reconciliacao[Reconciliation Agent]
            Compliance[Compliance Agent]
            Carrier[Carrier Agent]
            Expedition[Expedition Agent]
            Reverse[Reverse Agent]
            Observation[Observation Agent]
            EquipResearch[EquipmentResearch Agent]
            Learning[Learning Agent]
            SchemaEvol[SchemaEvolution Agent]
            Validation[Validation Agent]
        end

        subgraph "Tools"
            FileDetect[FileDetector]
            NFParser[NFParser]
            PGClient[PostgreSQL Client]
        end
    end

    subgraph "AWS Data Layer"
        RDS[(Aurora PostgreSQL\nPRIMARY DATASTORE\nInventory Data)]
        RDSProxy[RDS Proxy]
        DDBHIL[(DynamoDB\nHIL Tasks Table\n4 GSIs)]
        DDBAudit[(DynamoDB\nAudit Log Table\n4 GSIs)]
        DDBSessions[(DynamoDB\nSessions Table)]
        S3Docs[S3 Documents Bucket]
    end

    subgraph "External Services"
        Cognito[AWS Cognito]
        Gemini[Google Gemini 3.0\nPro + Flash]
    end

    User((User)) --> CF
    CF --> URLRw --> S3F
    S3F --> Pages
    Pages --> Contexts --> Hooks --> Services
    Services -->|JWT Auth| Runtime
    Runtime --> Memory
    Runtime --> A2A
    A2A --> EstoqueCtrl & Intake & Import & NexoImport & Reconciliacao & Compliance & Carrier & Expedition & Reverse & Observation & EquipResearch & Learning & SchemaEvol & Validation
    Intake & Import & NexoImport --> FileDetect
    Intake --> NFParser
    EstoqueCtrl & Intake & Import & NexoImport & Reconciliacao & Validation & SchemaEvol --> RDSProxy --> RDS
    EstoqueCtrl & Intake & Import & NexoImport --> DDBHIL
    EstoqueCtrl & Intake & Import & NexoImport & Reconciliacao --> DDBAudit
    Runtime --> DDBSessions
    Intake & Import & NexoImport --> S3Docs
    EstoqueCtrl & Intake & Import & NexoImport & Learning & Compliance --> Gemini
    Services -->|Token| Cognito
```

---

## 2. Frontend Route Structure

```mermaid
flowchart LR
    subgraph "/ferramentas/ativos/estoque"
        Dashboard["/\nDashboard"]

        subgraph "Asset Management"
            Lista["/lista\nAsset List"]
            Detail["/[id]\nAsset Detail"]
        end

        subgraph "/cadastros - Master Data"
            CadHub["/cadastros\nHub"]
            PN["/part-numbers\nPart Numbers"]
            Locais["/locais\nLocations"]
            Projetos["/projetos\nProjects"]
        end

        subgraph "/movimentacoes - Movements"
            MovHub["/movimentacoes\nHub"]
            Entrada["/entrada\nNF Entry"]
            Saida["/saida\nExpedition"]
            Transfer["/transferencia\nTransfer"]
            Reserva["/reserva\nReservation"]
            Ajuste["/ajuste\nAdjustment"]
        end

        subgraph "/inventario - Counting"
            InvList["/inventario\nCampaigns"]
            InvNew["/novo\nNew Campaign"]
            InvDetail["/[id]\nCounting"]
        end
    end

    Dashboard --> Lista & CadHub & MovHub & InvList
    Lista --> Detail
    CadHub --> PN & Locais & Projetos
    MovHub --> Entrada & Saida & Transfer & Reserva & Ajuste
    InvList --> InvNew & InvDetail
```

---

## 3. Context Provider Hierarchy

```mermaid
flowchart TB
    subgraph "Layout Provider Stack"
        QC[QueryClientProvider]
        AM[AssetManagementProvider\n- Master data: PN, Locations, Projects\n- Filters persistence\n- Dashboard summary]
        IO[InventoryOperationsProvider\n- Movement operations\n- Validation state\n- Operation status]
        TI[TaskInboxProvider\n- HIL tasks\n- Approval workflows\n- Polling]
        NE[NexoEstoqueProvider\n- AI chat history\n- Suggestions\n- Quick actions]
        IC[InventoryCountProvider\n- Campaigns\n- Counting sessions\n- Divergences]
        OS[OfflineSyncProvider\n- Network status\n- Sync queue\n- PWA support]
    end

    QC --> AM --> IO --> TI --> NE --> IC --> OS --> Pages[Page Components]

    style AM fill:#e1f5fe
    style IO fill:#fff3e0
    style TI fill:#fce4ec
    style NE fill:#f3e5f5
    style IC fill:#e8f5e9
    style OS fill:#fff8e1
```

---

## 4. Backend Agent Architecture (AWS Strands Agents)

```mermaid
flowchart TB
    subgraph "main.py - AgentCore Entry Point"
        Entry[@app.entrypoint\nA2A Handler]
        Router{Action Router}
    end

    subgraph "EstoqueControlAgent (Flash)"
        EC1[create_reservation]
        EC2[cancel_reservation]
        EC3[process_expedition]
        EC4[create_transfer]
        EC5[process_return]
        EC6[query_balance]
        EC7[query_asset_location]
    end

    subgraph "IntakeAgent (Pro + Thinking)"
        IA1[process_nf_upload]
        IA2[validate_nf_extraction]
        IA3[confirm_nf_entry]
        IA4[_match_items_to_pn]
    end

    subgraph "ImportAgent (Pro + Thinking)"
        IMP1[preview_import]
        IMP2[execute_import]
        IMP3[process_text_import]
        IMP4[_map_columns]
        IMP5[_extract_with_gemini]
    end

    subgraph "NexoImportAgent (Pro + Thinking)"
        NI1[smart_import_upload]
        NI2[validate_schema]
        NI3[interactive_qa]
        NI4[learn_from_import]
    end

    subgraph "ReconciliationAgent (Flash)"
        RA1[start_campaign]
        RA2[submit_count_result]
        RA3[analyze_divergences]
        RA4[propose_adjustment]
    end

    subgraph "ComplianceAgent (Pro)"
        CA1[validate_operation]
        CA2[check_approval_hierarchy]
        CA3[check_restricted_locations]
    end

    subgraph "CarrierAgent (Flash)"
        CR1[manage_carriers]
        CR2[track_shipment]
    end

    subgraph "ExpeditionAgent (Flash)"
        EX1[process_outbound]
        EX2[generate_shipping_label]
    end

    subgraph "ReverseAgent (Flash)"
        RV1[process_return]
        RV2[handle_reverse_logistics]
    end

    subgraph "ObservationAgent (Flash)"
        OB1[record_field_observation]
        OB2[analyze_patterns]
    end

    subgraph "EquipmentResearchAgent (Flash)"
        EQ1[search_equipment_kb]
        EQ2[find_specifications]
    end

    subgraph "LearningAgent (Pro + Thinking)"
        LA1[continuous_learning]
        LA2[improve_predictions]
        LA3[retrieve_prior_knowledge]
        LA4[create_episode]
    end

    subgraph "SchemaEvolutionAgent (Pro + Thinking)"
        SE1[create_column]
        SE2[modify_schema]
        SE3[validate_migration]
    end

    subgraph "ValidationAgent (Flash)"
        VA1[validate_data]
        VA2[check_constraints]
        VA3[verify_quality]
    end

    subgraph "Tools"
        PG[PostgreSQL Client]
        DDB[DynamoDB Client]
        S3C[S3 Client]
        HIL[HIL Workflow Manager]
        NFP[NFParser]
        FD[FileDetector]
    end

    Entry --> Router
    Router --> EC1 & EC2 & EC3 & EC4 & EC5 & EC6 & EC7
    Router --> IA1 & IA2 & IA3
    Router --> IMP1 & IMP2 & IMP3
    Router --> NI1 & NI2 & NI3 & NI4
    Router --> RA1 & RA2 & RA3 & RA4
    Router --> CA1
    Router --> CR1 & CR2
    Router --> EX1 & EX2
    Router --> RV1 & RV2
    Router --> OB1 & OB2
    Router --> EQ1 & EQ2
    Router --> LA1 & LA2 & LA3 & LA4
    Router --> SE1 & SE2 & SE3
    Router --> VA1 & VA2 & VA3

    EC1 & EC2 & EC3 & EC4 & EC5 --> PG & HIL
    IA1 & IA2 & IA3 --> PG & S3C & NFP & HIL
    IMP1 & IMP2 & IMP3 --> PG & S3C & FD & HIL
    NI1 & NI2 & NI3 & NI4 --> PG & S3C & FD & HIL
    RA1 & RA2 & RA3 & RA4 --> PG & HIL
    CA1 --> PG
    LA1 & LA2 & LA3 & LA4 --> DDB
    SE1 & SE2 & SE3 --> PG
    VA1 & VA2 & VA3 --> PG
```

---

## 5. Data Architecture

### Database Responsibilities

```mermaid
flowchart TB
    subgraph "Aurora PostgreSQL (PRIMARY)"
        PG1[part_numbers\nMaster catalog]
        PG2[assets\nSerialized items]
        PG3[locations\nWarehouse hierarchy]
        PG4[movements\nImmutable history]
        PG5[balances\nCurrent stock levels]
        PG6[reservations\nTTL-based]
    end

    subgraph "DynamoDB (SECONDARY)"
        DB1[HIL Tasks\nApproval workflows]
        DB2[Audit Log\nEvent sourcing]
        DB3[Sessions\nAgentCore memory]
    end

    subgraph "Agents"
        A1[NexoImportAgent]
        A2[IntakeAgent]
        A3[EstoqueControlAgent]
    end

    A1 & A2 & A3 -->|Inventory Data| PG1 & PG2 & PG3 & PG4 & PG5 & PG6
    A1 & A2 & A3 -->|HIL/Audit/Sessions| DB1 & DB2 & DB3
```

### PostgreSQL Schema (PRIMARY DATASTORE)

```mermaid
erDiagram
    PART_NUMBERS ||--o{ ASSETS : "defines"
    PART_NUMBERS ||--o{ MOVEMENTS : "tracks"
    PART_NUMBERS ||--o{ BALANCES : "stock"
    ASSETS ||--o{ MOVEMENTS : "history"
    LOCATIONS ||--o{ ASSETS : "contains"
    LOCATIONS ||--o{ MOVEMENTS : "from/to"
    LOCATIONS ||--o{ BALANCES : "stored_at"
    PART_NUMBERS ||--o{ RESERVATIONS : "reserves"
    LOCATIONS ||--o{ RESERVATIONS : "location"

    PART_NUMBERS {
        uuid pn_id PK
        varchar pn_code UNIQUE
        text description
        varchar uom
        varchar category
        jsonb metadata
    }

    ASSETS {
        uuid asset_id PK
        uuid pn_id FK
        varchar serial_number UNIQUE
        uuid location_id FK
        enum status
        enum condition
        jsonb metadata
    }

    LOCATIONS {
        uuid location_id PK
        varchar name
        varchar code UNIQUE
        enum type
        uuid parent_id FK
    }

    MOVEMENTS {
        uuid movement_id PK
        uuid asset_id FK
        uuid pn_id FK
        enum type
        integer quantity
        uuid from_location_id FK
        uuid to_location_id FK
        decimal confidence_score
        uuid hil_task_id
    }

    BALANCES {
        uuid balance_id PK
        uuid pn_id FK
        uuid location_id FK
        integer quantity
        integer reserved_quantity
        integer available_quantity
    }

    RESERVATIONS {
        uuid reservation_id PK
        uuid pn_id FK
        uuid location_id FK
        integer quantity
        enum status
        timestamptz expires_at
    }
```

### DynamoDB Tables (SECONDARY - Event/Workflow Data)

```mermaid
erDiagram
    HIL_TASKS_TABLE {
        string PK "TASK#task_id"
        string SK "METADATA | COMMENT#ts"
        string GSI1PK "ASSIGNEE#user_id"
        string GSI2PK "STATUS#status"
        string GSI3PK "TYPE#task_type"
        string GSI4PK "REF#entity#id"
        number ttl "90d approved, 30d expired"
    }

    AUDIT_LOG_TABLE {
        string PK "LOG#YYYY-MM-DD"
        string SK "timestamp#event_id"
        string GSI1PK "ACTOR#type#id"
        string GSI2PK "ENTITY#type#id"
        string GSI3PK "TYPE#event_type"
        string GSI4PK "SESSION#session_id"
    }

    SESSIONS_TABLE {
        string session_id PK
        string user_id
        string agent_name
        map memory
        string created_at
        string expires_at
        number TTL
    }

    HIL_TASKS_TABLE ||--o{ AUDIT_LOG_TABLE : "logs decisions"
```

---

## 6. A2A Protocol (TRUE Multi-Agent A2A Architecture)

### Architecture Overview

The SGA Inventory module uses **TRUE Multi-Agent A2A** architecture where:
- Each of 14 agents has its **OWN** `main.py` with Strands `A2AServer`
- **ORCHESTRATOR** (nexo_import) receives user requests and routes to specialists
- **SPECIALISTS** focus on specific domains (NF parsing, spreadsheet import, inventory control, memory)
- **SUPPORT** agents provide auxiliary functionality (validation, compliance, etc.)
- **ReAct Pattern**: OBSERVE→THINK→LEARN→EXECUTE + Human-in-the-Loop (HIL)

### Agent Roles

| Role | Agent(s) | Description |
|------|----------|-------------|
| **ORCHESTRATOR** | nexo_import | Routes requests to specialists, coordinates workflows |
| **SPECIALIST** | intake | NF-e parsing (XML, PDF, DANFE images via Gemini Vision) |
| **SPECIALIST** | import | CSV/XLSX bulk import with column mapping |
| **SPECIALIST** | estoque_control | Inventory movements, reservations, transfers |
| **SPECIALIST** | learning | AgentCore Memory (episodes, patterns, thresholds) |
| **SUPPORT** | validation | Schema and data validation |
| **SUPPORT** | compliance | Regulatory compliance checks |
| **SUPPORT** | observation | Audit trail and event logging |
| **SUPPORT** | schema_evolution | Dynamic column creation |
| **SUPPORT** | equipment_research | Equipment KB search |
| **SUPPORT** | carrier | Carrier management |
| **SUPPORT** | expedition | Outbound shipments |
| **SUPPORT** | reverse | Returns processing |
| **SUPPORT** | reconciliacao | SAP reconciliation |

### Configuration

| Property | Value |
|----------|-------|
| **Protocol** | JSON-RPC 2.0 |
| **Transport** | HTTP/HTTPS |
| **Port** | 9000 (per-agent) |
| **Entry Point** | `agents/<agent_id>/main.py` with Strands `A2AServer` |
| **Server** | `strands.multiagent.a2a.A2AServer` (serve_at_root=True) |
| **Discovery** | AWS Systems Manager Parameter Store (SSM) |
| **Authentication** | AWS IAM SigV4 + Cognito JWT |
| **Agent Card** | `/.well-known/agent-card.json` (A2A standard) |

### TRUE Multi-Agent A2A Flow

```mermaid
flowchart TB
    subgraph "User Request"
        User((User)) --> |"Import CSV"| GW[AgentCore Gateway]
    end

    subgraph "ORCHESTRATOR"
        GW --> Nexo[nexo_import\nORCHESTRATOR]
        Nexo -->|OBSERVE| Analyze["Analyze file type"]
        Analyze -->|CSV detected| Route["Route to specialist"]
    end

    subgraph "SPECIALISTS (via A2A)"
        Route -->|A2A| Import[import\nSPECIALIST]
        Import -->|preview_import| Preview[Preview columns]
        Import -->|detect_columns| Detect[Map columns]
        Import -->|A2A| Learn[learning\nSPECIALIST]
        Learn -->|retrieve_column_mappings| Prior["Prior patterns"]
        Prior --> Detect
        Detect -->|execute_import| Execute[Process rows]
        Execute -->|A2A| Estoque[estoque_control\nSPECIALIST]
        Estoque -->|create_entry_movement| Movements[Create movements]
    end

    subgraph "SUPPORT (via A2A)"
        Nexo -->|A2A| Obs[observation\nSUPPORT]
        Import -->|A2A| Obs
        Estoque -->|A2A| Obs
        Obs --> |log_event| Audit[(Audit Log)]
    end

    subgraph "Data Layer"
        Movements --> RDS[(Aurora PostgreSQL)]
        Estoque -->|HIL if confidence < 80%| HIL[(DynamoDB\nHIL Tasks)]
    end
```

### Message Format

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

## 7. AgentCore Memory Architecture

### Memory Types

```mermaid
flowchart TB
    subgraph "AgentCore Memory System"
        Session[Session Memory\nCurrent interaction working memory]
        STM[Short-Term Memory STM\nRecent decisions and context]
        LTM[Long-Term Memory LTM\nLearned patterns and schemas]
        RAG[RAG Retrieval-Augmented Generation\nEquipment KB embeddings]
    end

    subgraph "Memory Strategy"
        Strategy[Self-Managed Strategy\nCustom consolidation logic]
        Namespace[Global Namespace\n/strategy/import/company]
    end

    subgraph "Agents Using Memory"
        NI[NexoImportAgent]
        LA[LearningAgent]
        ER[EquipmentResearchAgent]
    end

    NI --> Session & STM & LTM
    LA --> STM & LTM
    ER --> RAG
    Session --> Strategy
    STM --> Strategy
    LTM --> Strategy
    Strategy --> Namespace
```

### Memory Configuration

| Agent | Session | STM | LTM | RAG | Strategy |
|-------|---------|-----|-----|-----|----------|
| **NexoImportAgent** | Yes | Yes | Yes | No | Self-Managed |
| **LearningAgent** | Yes | Yes | Yes | No | Self-Managed |
| **EquipmentResearchAgent** | Yes | No | No | Yes | Built-in |
| **Other Agents** | Yes | No | No | No | Built-in |

### Namespace Design

All import-related agents share a **GLOBAL namespace** to enable cross-company learning:

```
/strategy/import/company
```

This allows:
- Learned column mappings to be shared across companies
- Equipment patterns to be recognized globally
- Schema evolution patterns to be reused

### References

- [NEXO Memory Architecture](./NEXO_MEMORY_ARCHITECTURE.md)
- [ADR-001: GLOBAL Namespace Design](./ADR-001-global-namespace.md)
- [ADR-002: Self-Managed Strategy Pattern](./ADR-002-self-managed-strategy.md)
- [AWS Bedrock AgentCore Memory Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)

---

## 8. Gemini Model Selection

### Model Assignment Matrix (per ADR-003)

| Category | Model | Thinking | Count | Agents |
|----------|-------|----------|-------|--------|
| **Import/Analysis** | `gemini-3.0-pro` | HIGH | 5 | nexo_import, intake, import, learning, schema_evolution |
| **Complex Reasoning** | `gemini-3.0-pro` | None | 1 | compliance |
| **Operational** | `gemini-3.0-flash` | None | 8 | observation, validation, equipment_research, estoque_control, expedition, reverse, carrier, reconciliacao |

### Agent Model Configuration

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

### Why Gemini 3.0 Pro for Import Agents

Import agents perform complex file analysis:
1. **File Structure Understanding**: Parse XLSX/CSV with multiple sheets
2. **Column Mapping**: Match file columns to PostgreSQL schema
3. **Pattern Recognition**: Identify data types from sample values
4. **Schema Awareness**: Understand target database structure

These tasks benefit from:
- Extended context window (2M tokens)
- Deep reasoning capabilities
- Thinking mode for step-by-step analysis

### References

- [ADR-003: Gemini 3.0 Model Selection](./ADR-003-gemini-model-selection.md)
- [Google Gemini 3.0 Overview](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Gemini Thinking Mode](https://ai.google.dev/gemini-api/docs/thinking)

---

## 9. Smart Universal File Importer

The **Smart Import** is an intelligent importer that accepts ANY file format and automatically detects the type, routing to the appropriate agent.

### Philosophy: Observe → Think → Learn → Act

```mermaid
flowchart TB
    subgraph "OBSERVE"
        U((User)) -->|Drop File| UZ[SmartUploadZone]
        UZ -->|Detect| FD[FileDetector\nMagic Bytes]
    end

    subgraph "THINK"
        FD -->|Classify| Router{File Type\nRouter}
    end

    subgraph "LEARN"
        Router -->|XML/PDF/Image| IA[IntakeAgent\nNF Extraction]
        Router -->|CSV/XLSX| IMP[ImportAgent\nColumn Mapping]
        Router -->|TXT| TXT[ImportAgent\nGemini AI Text]
    end

    subgraph "ACT"
        IA -->|Preview| NFP[NFPreview]
        IMP -->|Preview| SSP[SpreadsheetPreview]
        TXT -->|Preview| TXP[TextPreview]

        NFP & SSP & TXP -->|Confidence Check| HIL{HIL\nRequired?}
        HIL -->|≥80%| AUTO[Autonomous\nConfirmation]
        HIL -->|<80%| REVIEW[Human\nReview]
    end

    AUTO -->|Create| MOV[(PostgreSQL\nMovements)]
    REVIEW -->|Approve| MOV
```

### Type Detection by Magic Bytes

```mermaid
flowchart TB
    subgraph "file_detector.py"
        FB[File Bytes] --> MB{Magic Bytes\nAnalysis}

        MB -->|"<?xml"| XML[XML\nNF]
        MB -->|"%PDF"| PDF[PDF\nDocument]
        MB -->|"0x89PNG"| PNG[PNG\nImage]
        MB -->|"0xFFD8"| JPG[JPEG\nImage]
        MB -->|"PK\x03\x04"| XLSX[XLSX\nSpreadsheet]
        MB -->|Extension| EXT{Extension\nFallback}

        EXT -->|.csv| CSV[CSV]
        EXT -->|.txt| TXT[Text]
        EXT -->|other| UNK[Unknown]
    end

    subgraph "Confidence Thresholds"
        CT1["XML: 90%"]
        CT2["PDF: 85%"]
        CT3["Image: 70%"]
        CT4["CSV/XLSX: 80%"]
        CT5["TXT: 60% (Always HIL)"]
    end
```

### Supported Formats

| Format | Magic Bytes | Agent | Base Confidence | Auto-Confirm |
|---------|------------|-------|----------------|--------------|
| **XML** | `<?xml` | IntakeAgent | 95% | ✅ Yes |
| **PDF** | `%PDF` | IntakeAgent | 85% | ✅ Yes |
| **JPG** | `0xFFD8` | IntakeAgent (Vision) | 70% | ⚠️ If >80% |
| **PNG** | `0x89PNG` | IntakeAgent (Vision) | 70% | ⚠️ If >80% |
| **CSV** | Extension | ImportAgent | 90% | ✅ If match >80% |
| **XLSX** | `PK\x03\x04` | ImportAgent | 90% | ✅ If match >80% |
| **TXT** | Extension | ImportAgent + Gemini | 60% | ❌ **Always HIL** |

---

## 10. NEXO Smart Import

**NEXO Smart Import** is the next-generation AI-powered import system that combines intelligent file processing with continuous learning capabilities.

### Key Features

```mermaid
flowchart TB
    subgraph "NEXO Import Pipeline"
        UP[User Upload] --> PF[Pre-Flight\nSchema Validation]
        PF -->|Valid| AI[AI Processing\nNexoImportAgent]
        PF -->|Invalid| ERR[Schema Error\nUser Feedback]

        AI --> QA[Interactive Q&A\nAmbiguous Data]
        QA --> PR[Preview\nReady for Processing]
        PR --> EX[Execute Import]
        EX --> LRN[Learning Loop\nStore Patterns]
    end

    subgraph "Core Capabilities"
        C1[PostgreSQL Schema\nIntrospection]
        C2[Real-time Validation\nBefore Processing]
        C3[Interactive Disambiguation\nQ&A Dialog]
        C4[Pattern Learning\nFrom Past Imports]
    end

    subgraph "Benefits"
        B1[Zero Invalid Imports\nCatch Errors Early]
        B2[Reduced HIL Tasks\nAI Learns User Preferences]
        B3[Faster Processing\nSmart Field Mapping]
    end
```

### Pre-Flight Validation Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant NI as NexoImportAgent
    participant PG as PostgreSQL
    participant VAL as SchemaValidator
    participant AI as Gemini 3.0 Pro

    U->>FE: Upload file
    FE->>NI: smart_import_upload()

    Note over NI: PRE-FLIGHT VALIDATION
    NI->>PG: Introspect schema
    PG-->>NI: Table structure, constraints

    NI->>VAL: Validate against schema

    alt Schema Valid
        VAL-->>NI: Validation passed
        NI->>AI: Process with context (Thinking HIGH)
        AI-->>NI: Extracted data + confidence

        alt High Confidence (≥80%)
            NI-->>FE: Preview (ready_for_processing)
        else Low Confidence
            NI-->>FE: Interactive Q&A required
            U->>FE: Answer questions
            FE->>NI: User responses
            NI->>AI: Re-process with answers
            AI-->>NI: Updated data
            NI-->>FE: Preview (ready_for_processing)
        end

        U->>FE: Confirm import
        FE->>NI: execute_import()
        NI->>PG: Insert validated data
        NI->>NI: Learn from successful import
        NI-->>FE: Success + learning stored

    else Schema Invalid
        VAL-->>NI: Validation errors
        NI-->>FE: Schema violation details
        FE-->>U: Show errors + suggestions
    end
```

### Learning Patterns

The NEXO Import Agent continuously improves by:

1. **Field Mapping Memory**: Remembers successful column → database field mappings
2. **Data Pattern Recognition**: Learns common data formats (dates, part numbers, locations)
3. **User Preference Learning**: Adapts to how specific users prefer to resolve ambiguities
4. **Error Prevention**: Stores past validation errors to prevent recurrence

---

## 11. NF Entry Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant AC as AgentCore
    participant IA as IntakeAgent
    participant S3 as S3 Bucket
    participant PG as PostgreSQL
    participant HIL as HIL Tasks

    U->>FE: Upload NF (XML/PDF)
    FE->>AC: getNFUploadUrl()
    AC->>S3: Generate presigned URL
    S3-->>FE: Presigned URL (15min)
    FE->>S3: PUT file to presigned URL

    FE->>AC: processNFUpload(s3_key)
    AC->>IA: process_nf_upload()
    IA->>S3: Download NF file

    alt XML File
        IA->>IA: Parse XML (stdlib)
    else PDF File
        IA->>IA: AI Extraction (Gemini 3.0 Pro)
    end

    IA->>IA: Match items to Part Numbers
    Note over IA: 3 strategies:\n1. Supplier code (95%)\n2. Description fuzzy (70%)\n3. NCM match (60%)

    IA->>PG: Save extraction
    IA-->>FE: NFExtraction + Confidence Score

    U->>FE: Review & Confirm Mappings
    FE->>AC: confirmNFEntry(mappings)
    AC->>IA: confirm_entry()

    alt Confidence >= 80% & All Matched
        IA->>PG: Create ENTRY movements
        IA->>PG: Update balances
        IA->>PG: Create/Update assets
        IA-->>FE: Success (autonomous)
    else Low Confidence or Unmatched
        IA->>HIL: Create APPROVAL_ENTRY task
        IA-->>FE: Pending HIL approval
    end
```

---

## 12. Reservation and Expedition Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant AC as AgentCore
    participant EC as EstoqueControlAgent
    participant CP as ComplianceAgent
    participant PG as PostgreSQL
    participant HIL as HIL Tasks

    %% Reservation
    U->>FE: Create Reservation (PN, Qty, Project)
    FE->>AC: createReservation()
    AC->>EC: create_reservation()
    EC->>PG: Check available balance

    alt Balance Sufficient
        EC->>CP: validate_operation()
        CP-->>EC: Validation result

        alt Same Project
            EC->>PG: Create RESERVE record
            EC->>PG: Update reserved balance
            EC-->>FE: Reservation created (autonomous)
        else Cross-Project
            EC->>HIL: Create APPROVAL_TRANSFER task
            EC-->>FE: Pending manager approval
        end
    else Insufficient Balance
        EC-->>FE: Error: Insufficient balance
    end

    %% Expedition
    U->>FE: Process Expedition
    FE->>AC: processExpedition(reservation_id)
    AC->>EC: process_expedition()
    EC->>PG: Validate reservation exists
    EC->>PG: Create EXIT movement
    EC->>PG: Update asset status → IN_TRANSIT
    EC->>PG: Release reservation
    EC->>PG: Update available balance
    EC-->>FE: Expedition processed
```

---

## 13. Inventory Counting Flow

```mermaid
sequenceDiagram
    participant M as Manager
    participant O as Operator
    participant FE as Frontend
    participant AC as AgentCore
    participant RA as ReconciliationAgent
    participant PG as PostgreSQL
    participant HIL as HIL Tasks

    %% Create Campaign
    M->>FE: Create Campaign (locations[], PNs[])
    FE->>AC: startCampaign()
    AC->>RA: start_campaign()
    RA->>PG: Create campaign record
    RA->>PG: Generate items_to_count[]
    RA-->>FE: Campaign created (DRAFT)

    %% Counting
    M->>FE: Activate Campaign
    FE->>AC: activateCampaign()

    loop For each location
        O->>FE: Start Counting Session
        FE->>AC: startCountingSession(location)

        loop For each item
            O->>FE: Scan Serial / Enter Qty
            FE->>AC: submitCountResult()
            AC->>RA: submit_count()
            RA->>PG: Record count result

            alt Divergence Detected
                RA->>PG: Create divergence record
                RA-->>FE: Divergence detected!
            end
        end
    end

    %% Analysis
    M->>FE: Analyze Divergences
    FE->>AC: analyzeDivergences()
    AC->>RA: analyze_divergences()
    RA-->>FE: Divergences[] + Summary

    %% Adjustment (ALWAYS HIL)
    M->>FE: Propose Adjustment
    FE->>AC: proposeAdjustment()
    AC->>RA: propose_adjustment()
    RA->>HIL: Create APPROVAL_ADJUSTMENT task
    Note over HIL: Adjustments ALWAYS require approval
    RA-->>FE: Pending approval

    %% Approval
    M->>FE: Approve Adjustment
    FE->>AC: approveTask(task_id)
    AC->>PG: Create ADJUSTMENT movement
    AC->>PG: Update balance
    AC-->>FE: Adjustment applied
```

---

## 14. HIL Workflow (Human-in-the-Loop)

```mermaid
stateDiagram-v2
    [*] --> PENDING: Task Created

    PENDING --> APPROVED: Manager Approves
    PENDING --> REJECTED: Manager Rejects
    PENDING --> EXPIRED: TTL Exceeded (30d)

    APPROVED --> [*]: Action Executed
    REJECTED --> [*]: Logged & Closed
    EXPIRED --> [*]: Auto-closed

    note right of PENDING
        Task Types:
        - APPROVAL_NEW_PN
        - APPROVAL_ENTRY
        - APPROVAL_ADJUSTMENT
        - APPROVAL_DISCARD
        - APPROVAL_TRANSFER
        - REVIEW_ENTRY
        - ESCALATION
    end note

    note right of APPROVED
        On Approval:
        1. Execute pending action
        2. Update inventory (PostgreSQL)
        3. Log to audit trail (DynamoDB)
        4. Notify requestor
    end note
```

### HIL Decision Matrix

| Operation | Condition | Decision |
|----------|----------|---------|
| Same-project reservation | - | ✅ Autonomous |
| Cross-project reservation | - | 🔒 HIL Required |
| Normal transfer | - | ✅ Autonomous |
| Transfer to VAULT/QUARANTINE | - | 🔒 HIL Required |
| NF Entry | Confidence ≥ 80% | ✅ Autonomous |
| NF Entry | Confidence < 80% | 🔒 HIL Required |
| NF Entry | Unmapped items | 🔒 HIL Required |
| Inventory adjustment | Any | 🔒 **ALWAYS** HIL |
| Discard/Loss | Any | 🔒 **ALWAYS** HIL |
| New Part Number | Any | 🔒 HIL Required |

---

## 15. S3 Documents Structure

```mermaid
flowchart TB
    subgraph "faiston-one-sga-documents-prod"
        subgraph "notas-fiscais/{YYYY}/{MM}/{nf_id}/"
            NF1[original.pdf]
            NF2[original.xml]
            NF3[extraction.json]
            NF4[thumbnail.jpg]
        end

        subgraph "evidences/{movement_id}/"
            EV1[photos/]
            EV2[signatures/]
            EV3[documents/]
        end

        subgraph "inventories/{campaign_id}/"
            INV1[photos/]
            INV2[exports/]
        end

        TEMP[temp/uploads/]
    end

    subgraph "Lifecycle Rules"
        L1[temp/ → Delete 1 day]
        L2[notas-fiscais/ → STANDARD_IA 90d → GLACIER 2y]
        L3[evidences/ → STANDARD_IA 180d → GLACIER 2y → DEEP_ARCHIVE 5y]
    end
```

---

## 16. Key Frontend Components

### NEXO AI Components

```mermaid
flowchart TB
    subgraph "NEXO Inventory Components"
        NC[NexoCopilot]
        NS[NexoSearchBar]
        US[UnifiedSearch]
    end

    subgraph "NexoCopilot Features"
        CH[Chat History\nMarkdown Rendering]
        QA[Quick Actions\n7 predefined queries]
        SG[Suggestions\nAI-generated next steps]
        MI[Message Input\nSend/Clear]
    end

    NC --> CH & QA & SG & MI

    subgraph "Quick Actions"
        Q1["Check balance"]
        Q2["Locate serial"]
        Q3["Pending returns"]
        Q4["My tasks"]
        Q5["Items below minimum"]
        Q6["Today's movements"]
        Q7["Equipment search"]
    end

    QA --> Q1 & Q2 & Q3 & Q4 & Q5 & Q6 & Q7
```

### Mobile/PWA Components

```mermaid
flowchart LR
    subgraph "Mobile Components"
        MS[MobileScanner\nBarcode/QR]
        MC[MobileChecklist\nProgressive Counting]
        CB[ConfirmationButton\nVisual Feedback]
    end

    subgraph "OfflineSyncContext"
        NW[Network Status]
        SQ[Sync Queue]
        FS[Force Sync]
    end

    MS & MC & CB --> SQ
    NW -->|Online| FS
```

---

## 17. AWS Infrastructure Summary

| Resource | Name | Purpose |
|---------|------|-----------|
| **Aurora PostgreSQL** | `faiston-one-sga-postgres-prod` | Primary inventory datastore |
| **RDS Proxy** | `faiston-one-sga-proxy-prod` | Connection pooling for Lambda |
| **DynamoDB** | `faiston-one-sga-hil-tasks-prod` | Approval tasks (4 GSIs) |
| **DynamoDB** | `faiston-one-sga-audit-log-prod` | Immutable audit trail (4 GSIs) |
| **DynamoDB** | `faiston-one-sga-sessions-prod` | AgentCore session memory |
| **S3** | `faiston-one-sga-documents-prod` | NF, evidence, photos |
| **IAM Role** | `faiston-one-sga-agentcore-role` | AgentCore execution |
| **CloudFront** | `faiston-one-cdn` | CDN with URL Rewriter |
| **Cognito** | Shared pool | JWT authentication |

### Region and Account

- **AWS Account**: `377311924364`
- **Region**: `us-east-2` (Ohio)
- **Terraform State**: S3 + DynamoDB locking

---

## 18. Related Documentation

### Architecture
- [Agent Catalog](../AGENT_CATALOG.md) - Complete agent inventory
- [NEXO Memory Architecture](./NEXO_MEMORY_ARCHITECTURE.md) - Memory system design
- [Database Schema](../DATABASE_SCHEMA.md) - PostgreSQL and DynamoDB schemas
- [ADR-001: GLOBAL Namespace Design](./ADR-001-global-namespace.md)
- [ADR-002: Self-Managed Strategy Pattern](./ADR-002-self-managed-strategy.md)
- [ADR-003: Gemini 3.0 Model Selection](./ADR-003-gemini-model-selection.md)

### Implementation
- [AgentCore Implementation Guide](../AgentCore/IMPLEMENTATION_GUIDE.md)
- [Infrastructure](../INFRASTRUCTURE.md)
- [Troubleshooting](../TROUBLESHOOTING.md)

### Frontend
- **Routes**: `client/app/(main)/ferramentas/ativos/estoque/`
- **Components**: `client/components/ferramentas/ativos/estoque/`
- **Contexts**: `client/contexts/ativos/`
- **Hooks**: `client/hooks/ativos/`
- **Services**: `client/services/sgaAgentcore.ts`
- **Types**: `client/lib/ativos/types.ts`

### Backend
- **Main**: `server/agentcore-inventory/main.py`
- **Agents**: `server/agentcore-inventory/dist/{agent_name}/`
- **Tools**: `server/agentcore-inventory/tools/`
  - `file_detector.py` - Magic bytes file type detection

### Smart Import
- **Types**: `client/lib/ativos/smartImportTypes.ts`
- **Hook**: `client/hooks/ativos/useSmartImporter.ts`
- **Components**:
  - `SmartUploadZone.tsx` - Universal drag-and-drop
  - `SmartPreview.tsx` - Preview router
  - `previews/NFPreview.tsx` - NF preview
  - `previews/SpreadsheetPreview.tsx` - CSV/XLSX preview
  - `previews/TextPreview.tsx` - AI text preview

### Infrastructure
- **DynamoDB**: `terraform/main/dynamodb_sga_*.tf`
- **S3**: `terraform/main/s3_sga_documents.tf`
- **IAM**: `terraform/main/iam_sga_agentcore.tf`
- **CloudFront**: `terraform/main/cloudfront.tf`
- **RDS**: `terraform/main/rds_aurora_postgres.tf`

---

**Platform**: Faiston NEXO
**Last Updated**: January 2026
**Version**: 3.0 - Architecture corrected to reflect actual implementation
**Total Agents**: 14 (estoque_control, nexo_import, intake, import, learning, schema_evolution, validation, compliance, reconciliacao, observation, equipment_research, carrier, expedition, reverse)
**Framework**: AWS Strands Agents Framework + Google ADK v1.0
**Models**: Gemini 3.0 Pro (6 agents with Thinking) + Gemini 3.0 Flash (8 agents)
**Primary Datastore**: Aurora PostgreSQL (inventory data)
**Secondary Datastore**: DynamoDB (HIL tasks, audit logs, sessions)
**Communication**: A2A Protocol (JSON-RPC 2.0) on Port 9000
**Memory**: AgentCore Memory (Session + STM + LTM + RAG)
