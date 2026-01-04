# Arquitetura do Módulo SGA Estoque - Faiston NEXO

## Visão Geral

O módulo **SGA Estoque** (Sistema de Gestão de Ativos - Estoque) é um sistema completo de gestão de inventário com recursos de IA, workflows de aprovação humana (HIL), e suporte offline/PWA.

---

## 1. Arquitetura de Alto Nível

```mermaid
flowchart TB
    subgraph "Frontend - Next.js 15"
        CF[CloudFront CDN]
        S3F[S3 Frontend Bucket]
        URLRw[URL Rewriter Function]
    end

    subgraph "Cliente React"
        Pages[15+ Pages/Routes]
        Contexts[6 Contexts]
        Hooks[12 Hooks]
        Services[sgaAgentcore.ts]
    end

    subgraph "AWS Bedrock AgentCore"
        Runtime[AgentCore Runtime]
        Memory[AgentCore Memory STM]

        subgraph "Google ADK Agents"
            EstoqueCtrl[EstoqueControl Agent]
            Intake[Intake Agent]
            Reconciliacao[Reconciliacao Agent]
            Compliance[Compliance Agent]
            Comunicacao[Comunicacao Agent]
        end
    end

    subgraph "AWS Data Layer"
        DDBInv[(DynamoDB\nInventory Table\n6 GSIs)]
        DDBHIL[(DynamoDB\nHIL Tasks Table\n4 GSIs)]
        DDBAudit[(DynamoDB\nAudit Log Table\n4 GSIs)]
        S3Docs[S3 Documents Bucket]
    end

    subgraph "External Services"
        Cognito[AWS Cognito]
        Gemini[Google Gemini 3.0 Pro]
    end

    User((Usuário)) --> CF
    CF --> URLRw --> S3F
    S3F --> Pages
    Pages --> Contexts --> Hooks --> Services
    Services -->|JWT Auth| Runtime
    Runtime --> Memory
    Runtime --> EstoqueCtrl & Intake & Reconciliacao & Compliance & Comunicacao
    EstoqueCtrl & Intake & Reconciliacao --> DDBInv
    EstoqueCtrl & Intake --> DDBHIL
    EstoqueCtrl & Intake & Reconciliacao --> DDBAudit
    Intake --> S3Docs
    EstoqueCtrl & Intake --> Gemini
    Services -->|Token| Cognito
```

---

## 2. Estrutura de Rotas do Frontend

```mermaid
flowchart LR
    subgraph "/ferramentas/ativos/estoque"
        Dashboard["/\nDashboard"]

        subgraph "Asset Management"
            Lista["/lista\nLista de Ativos"]
            Detail["/[id]\nDetalhe do Ativo"]
        end

        subgraph "/cadastros - Master Data"
            CadHub["/cadastros\nHub"]
            PN["/part-numbers\nPart Numbers"]
            Locais["/locais\nLocalizações"]
            Projetos["/projetos\nProjetos"]
        end

        subgraph "/movimentacoes - Movements"
            MovHub["/movimentacoes\nHub"]
            Entrada["/entrada\nEntrada NF-e"]
            Saida["/saida\nExpedição"]
            Transfer["/transferencia\nTransferência"]
            Reserva["/reserva\nReserva"]
            Ajuste["/ajuste\nAjuste"]
        end

        subgraph "/inventario - Counting"
            InvList["/inventario\nCampanhas"]
            InvNew["/novo\nNova Campanha"]
            InvDetail["/[id]\nContagem"]
        end
    end

    Dashboard --> Lista & CadHub & MovHub & InvList
    Lista --> Detail
    CadHub --> PN & Locais & Projetos
    MovHub --> Entrada & Saida & Transfer & Reserva & Ajuste
    InvList --> InvNew & InvDetail
```

---

## 3. Hierarquia de Context Providers

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

## 4. Arquitetura dos Agentes Backend (Google ADK)

```mermaid
flowchart TB
    subgraph "main.py - 40 Actions Router"
        Router{Action Router}
    end

    subgraph "EstoqueControlAgent"
        EC1[create_reservation]
        EC2[cancel_reservation]
        EC3[process_expedition]
        EC4[create_transfer]
        EC5[process_return]
        EC6[query_balance]
        EC7[query_asset_location]
    end

    subgraph "IntakeAgent"
        IA1[process_nf_upload]
        IA2[validate_nf_extraction]
        IA3[confirm_nf_entry]
        IA4[_match_items_to_pn]
    end

    subgraph "ReconciliacaoAgent"
        RA1[start_campaign]
        RA2[submit_count_result]
        RA3[analyze_divergences]
        RA4[propose_adjustment]
    end

    subgraph "ComplianceAgent"
        CA1[validate_operation]
        CA2[check_approval_hierarchy]
        CA3[check_restricted_locations]
    end

    subgraph "ComunicacaoAgent"
        CM1[send_notification]
        CM2[send_reminder]
        CM3[send_escalation]
    end

    subgraph "Tools"
        DDB[SGADynamoDBClient]
        S3C[SGAS3Client]
        HIL[HILWorkflowManager]
        NFP[NFParser]
    end

    Router --> EC1 & EC2 & EC3 & EC4 & EC5 & EC6 & EC7
    Router --> IA1 & IA2 & IA3
    Router --> RA1 & RA2 & RA3 & RA4
    Router --> CA1
    Router --> CM1 & CM2 & CM3

    EC1 & EC2 & EC3 & EC4 & EC5 --> DDB & HIL
    IA1 & IA2 & IA3 --> DDB & S3C & NFP & HIL
    RA1 & RA2 & RA3 & RA4 --> DDB & HIL
    CA1 --> DDB
    CM1 & CM2 --> DDB
```

---

## 5. Modelo de Dados DynamoDB (Single-Table Design)

```mermaid
erDiagram
    INVENTORY_TABLE {
        string PK "ENTITY#id"
        string SK "METADATA | context#key"
        string GSI1PK "SERIAL#serial_number"
        string GSI2PK "LOC#location_id"
        string GSI3PK "PROJ#project_id"
        string GSI4PK "STATUS#status"
        string GSI5PK "DATE#YYYY-MM"
        string GSI6PK "TIMELINE#asset_id"
        number ttl "TTL for reservations"
    }

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

    INVENTORY_TABLE ||--o{ HIL_TASKS_TABLE : "creates tasks"
    INVENTORY_TABLE ||--o{ AUDIT_LOG_TABLE : "logs events"
    HIL_TASKS_TABLE ||--o{ AUDIT_LOG_TABLE : "logs decisions"
```

### Prefixos de Entidade (PK Pattern)

| Prefixo | Entidade | Exemplo PK |
|---------|----------|------------|
| `PN#` | Part Number | `PN#pn_001` |
| `ASSET#` | Ativo Serializado | `ASSET#asset_123` |
| `LOC#` | Localização | `LOC#loc_warehouse_01` |
| `BALANCE#` | Saldo Projetado | `BALANCE#pn_001#loc_01` |
| `MOVE#` | Movimento (Imutável) | `MOVE#move_456` |
| `RESERVE#` | Reserva (TTL) | `RESERVE#res_789` |
| `TASK#` | Tarefa HIL | `TASK#task_abc` |
| `DIV#` | Divergência | `DIV#div_xyz` |
| `DOC#` | Documento | `DOC#nf_12345` |
| `PROJ#` | Projeto | `PROJ#proj_cliente_01` |

---

## 6. Fluxo de Entrada via NF-e

```mermaid
sequenceDiagram
    participant U as Usuário
    participant FE as Frontend
    participant AC as AgentCore
    participant IA as IntakeAgent
    participant S3 as S3 Bucket
    participant DDB as DynamoDB
    participant HIL as HIL Tasks

    U->>FE: Upload NF-e (XML/PDF)
    FE->>AC: getNFUploadUrl()
    AC->>S3: Generate presigned URL
    S3-->>FE: Presigned URL (15min)
    FE->>S3: PUT file to presigned URL

    FE->>AC: processNFUpload(s3_key)
    AC->>IA: process_nf_upload()
    IA->>S3: Download NF-e file

    alt XML File
        IA->>IA: Parse XML (stdlib)
    else PDF File
        IA->>IA: AI Extraction (Gemini)
    end

    IA->>IA: Match items to Part Numbers
    Note over IA: 3 strategies:\n1. Supplier code (95%)\n2. Description fuzzy (70%)\n3. NCM match (60%)

    IA->>DDB: Save extraction
    IA-->>FE: NFExtraction + Confidence Score

    U->>FE: Review & Confirm Mappings
    FE->>AC: confirmNFEntry(mappings)
    AC->>IA: confirm_entry()

    alt Confidence >= 80% & All Matched
        IA->>DDB: Create ENTRY movements
        IA->>DDB: Update balances
        IA->>DDB: Create/Update assets
        IA-->>FE: Success (autonomous)
    else Low Confidence or Unmatched
        IA->>HIL: Create APPROVAL_ENTRY task
        IA-->>FE: Pending HIL approval
    end
```

---

## 7. Fluxo de Reserva e Expedição

```mermaid
sequenceDiagram
    participant U as Usuário
    participant FE as Frontend
    participant AC as AgentCore
    participant EC as EstoqueControlAgent
    participant CP as ComplianceAgent
    participant DDB as DynamoDB
    participant HIL as HIL Tasks

    %% Reserva
    U->>FE: Criar Reserva (PN, Qty, Projeto)
    FE->>AC: createReservation()
    AC->>EC: create_reservation()
    EC->>DDB: Check available balance

    alt Balance Sufficient
        EC->>CP: validate_operation()
        CP-->>EC: Validation result

        alt Same Project
            EC->>DDB: Create RESERVE#
            EC->>DDB: Update reserved balance
            EC-->>FE: Reservation created (autonomous)
        else Cross-Project
            EC->>HIL: Create APPROVAL_TRANSFER task
            EC-->>FE: Pending manager approval
        end
    else Insufficient Balance
        EC-->>FE: Error: Saldo insuficiente
    end

    %% Expedição
    U->>FE: Processar Expedição
    FE->>AC: processExpedition(reservation_id)
    AC->>EC: process_expedition()
    EC->>DDB: Validate reservation exists
    EC->>DDB: Create EXIT movement
    EC->>DDB: Update asset status → IN_TRANSIT
    EC->>DDB: Release reservation
    EC->>DDB: Update available balance
    EC-->>FE: Expedition processed
```

---

## 8. Fluxo de Contagem de Inventário

```mermaid
sequenceDiagram
    participant M as Manager
    participant O as Operador
    participant FE as Frontend
    participant AC as AgentCore
    participant RA as ReconciliacaoAgent
    participant DDB as DynamoDB
    participant HIL as HIL Tasks

    %% Criar Campanha
    M->>FE: Criar Campanha (locations[], PNs[])
    FE->>AC: startCampaign()
    AC->>RA: start_campaign()
    RA->>DDB: Create campaign record
    RA->>DDB: Generate items_to_count[]
    RA-->>FE: Campaign created (DRAFT)

    %% Contagem
    M->>FE: Ativar Campanha
    FE->>AC: activateCampaign()

    loop For each location
        O->>FE: Iniciar Sessão de Contagem
        FE->>AC: startCountingSession(location)

        loop For each item
            O->>FE: Escanear Serial / Informar Qty
            FE->>AC: submitCountResult()
            AC->>RA: submit_count()
            RA->>DDB: Record count result

            alt Divergence Detected
                RA->>DDB: Create DIV# record
                RA-->>FE: Divergência detectada!
            end
        end
    end

    %% Análise
    M->>FE: Analisar Divergências
    FE->>AC: analyzeDivergences()
    AC->>RA: analyze_divergences()
    RA-->>FE: Divergences[] + Summary

    %% Ajuste (SEMPRE HIL)
    M->>FE: Propor Ajuste
    FE->>AC: proposeAdjustment()
    AC->>RA: propose_adjustment()
    RA->>HIL: Create APPROVAL_ADJUSTMENT task
    Note over HIL: Ajustes SEMPRE requerem aprovação
    RA-->>FE: Pending approval

    %% Aprovação
    M->>FE: Aprovar Ajuste
    FE->>AC: approveTask(task_id)
    AC->>DDB: Create ADJUSTMENT movement
    AC->>DDB: Update balance
    AC-->>FE: Adjustment applied
```

---

## 9. Workflow HIL (Human-in-the-Loop)

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
        2. Update inventory
        3. Log to audit trail
        4. Notify requestor
    end note
```

### Matriz de Decisão HIL

| Operação | Condição | Decisão |
|----------|----------|---------|
| Reserva mesmo projeto | - | ✅ Autônomo |
| Reserva cross-project | - | 🔒 HIL Obrigatório |
| Transferência normal | - | ✅ Autônomo |
| Transferência p/ COFRE/QUARENTENA | - | 🔒 HIL Obrigatório |
| Entrada NF-e | Confidence ≥ 80% | ✅ Autônomo |
| Entrada NF-e | Confidence < 80% | 🔒 HIL Obrigatório |
| Entrada NF-e | Itens não mapeados | 🔒 HIL Obrigatório |
| Ajuste de inventário | Qualquer | 🔒 **SEMPRE** HIL |
| Descarte/Perda | Qualquer | 🔒 **SEMPRE** HIL |
| Novo Part Number | Qualquer | 🔒 HIL Obrigatório |

---

## 10. Estrutura S3 Documents

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

## 11. Componentes Frontend Chave

### NEXO AI Components

```mermaid
flowchart TB
    subgraph "NEXO Estoque Components"
        NC[NexoCopilot]
        NS[NexoSearchBar]
        US[UnifiedSearch]
    end

    subgraph "NexoCopilot Features"
        CH[Chat History\nMarkdown Rendering]
        QA[Quick Actions\n6 predefined queries]
        SG[Suggestions\nAI-generated next steps]
        MI[Message Input\nSend/Clear]
    end

    NC --> CH & QA & SG & MI

    subgraph "Quick Actions"
        Q1["Verificar saldo"]
        Q2["Localizar serial"]
        Q3["Reversas pendentes"]
        Q4["Minhas tarefas"]
        Q5["Itens abaixo mínimo"]
        Q6["Movimentações hoje"]
    end

    QA --> Q1 & Q2 & Q3 & Q4 & Q5 & Q6
```

### Mobile/PWA Components

```mermaid
flowchart LR
    subgraph "Mobile Components"
        MS[MobileScanner\nBarcode/QR]
        MC[MobileChecklist\nContagem Progressiva]
        CB[ConfirmationButton\nFeedback Visual]
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

## 12. Resumo da Infraestrutura AWS

| Recurso | Nome | Propósito |
|---------|------|-----------|
| **DynamoDB** | `faiston-one-sga-inventory-prod` | Tabela principal (6 GSIs, Streams) |
| **DynamoDB** | `faiston-one-sga-hil-tasks-prod` | Tarefas de aprovação (4 GSIs) |
| **DynamoDB** | `faiston-one-sga-audit-log-prod` | Audit trail imutável (4 GSIs) |
| **S3** | `faiston-one-sga-documents-prod` | NF-e, evidências, fotos |
| **IAM Role** | `faiston-one-sga-agentcore-role` | Execução AgentCore |
| **CloudFront** | `faiston-one-cdn` | CDN com URL Rewriter |
| **Cognito** | Pool compartilhado | Autenticação JWT |

### Região e Conta

- **AWS Account**: `377311924364`
- **Region**: `us-east-2` (Ohio)
- **Terraform State**: S3 + DynamoDB locking

---

## Arquivos Relacionados

### Frontend
- **Routes**: `client/app/(main)/ferramentas/ativos/estoque/`
- **Components**: `client/components/ferramentas/ativos/estoque/`
- **Contexts**: `client/contexts/ativos/`
- **Hooks**: `client/hooks/ativos/`
- **Services**: `client/services/sgaAgentcore.ts`
- **Types**: `client/lib/ativos/types.ts`

### Backend
- **Main**: `server/agentcore-inventory/main.py`
- **Agents**: `server/agentcore-inventory/agents/`
- **Tools**: `server/agentcore-inventory/tools/`

### Infrastructure
- **DynamoDB**: `terraform/main/dynamodb_sga_*.tf`
- **S3**: `terraform/main/s3_sga_documents.tf`
- **IAM**: `terraform/main/iam_sga_agentcore.tf`
- **CloudFront**: `terraform/main/cloudfront.tf`

---

*Documento gerado em: 2026-01-04*
*Versão: 1.0*
