# PRD: Tavily Data Enrichment Module

## Product Requirements Document

**Product Name:** NEXO Tavily Data Enrichment Module
**Version:** 1.0
**Created:** 2026-01-13
**Status:** Draft
**Product Owner:** Fabio Santos

---

## 1. Executive Summary

### 1.1 Product Vision

Transform NEXO from a simple inventory management system into an **intelligent knowledge platform** that automatically enriches imported equipment data with official specifications, manuals, and compatibility information from authoritative sources worldwide.

### 1.2 Problem Statement

**Para:** Faiston IT Operations Team
**Que:** Need comprehensive technical information about equipment after importing inventory data
**O:** NEXO Tavily Data Enrichment Module
**É uma:** AI-powered data enrichment pipeline
**Que:** Automatically researches and aggregates official equipment specifications, manuals, pricing, and compatibility data
**Diferentemente de:** Manual Google searches or maintaining static specification databases
**Nosso produto:** Uses AI-optimized search (Tavily) with AWS Strands Agents to create a self-updating knowledge base accessible via natural language through NEXO Assistant

### 1.3 Target Users

| Persona | Description | Primary Need |
|---------|-------------|--------------|
| **IT Operations Technician** | Daily equipment handler | Quick access to specs, manuals, and troubleshooting guides |
| **Inventory Manager** | Tracks equipment lifecycle | Validated part numbers, EOL dates, warranty info |
| **IT Manager** | Strategic planning | Compatibility matrices, upgrade paths, pricing trends |
| **Procurement Team** | Equipment acquisition | Current market prices, vendor comparison |

---

## 2. Goals & Success Metrics

### 2.1 Business Goals

1. **Reduce manual research time** from 15-30 min/equipment to <1 minute
2. **Increase data accuracy** by cross-referencing multiple official sources
3. **Enable proactive maintenance** through EOL/EOS date tracking
4. **Support procurement decisions** with real-time market intelligence

### 2.2 User Goals

1. Ask NEXO Assistant about any equipment and get immediate, accurate answers
2. Access official manuals/datasheets without leaving the platform
3. Receive alerts about equipment reaching end-of-life
4. Compare equipment specifications across vendors

### 2.3 Key Performance Indicators (KPIs)

| KPI | Description | Target |
|-----|-------------|--------|
| **Enrichment Coverage** | % of imported equipment with enriched data | ≥95% |
| **Data Accuracy** | Manual validation sample accuracy | ≥98% |
| **Enrichment Time** | Average time per equipment item | <30 seconds |
| **Source Quality** | % of data from official/vendor sources | ≥80% |
| **RAG Response Accuracy** | NEXO Assistant answer correctness | ≥90% |
| **User Time Saved** | Reduction in manual research time | ≥80% |

---

## 3. User Experience Requirements

### 3.1 Design Philosophy

**Invisible Intelligence** - The enrichment process should be completely automatic and transparent. Users interact only with the results through NEXO Assistant, never with the enrichment pipeline itself.

### 3.2 Core UX Principles

1. **Zero-Click Enrichment**: Data enrichment happens automatically post-import
2. **Natural Language Access**: All enriched data accessible via conversational queries
3. **Confidence Transparency**: NEXO Assistant indicates data source and confidence level
4. **Progressive Disclosure**: Basic info immediately, detailed specs on request

### 3.3 User Interaction Examples

```
User: "What are the specs of serial number ABC123?"
NEXO: "Serial ABC123 is a Cisco C9200-24P switch:
       - 24x 1GbE PoE+ ports (370W budget)
       - 4x 10G SFP+ uplinks
       - 128GB SSD storage
       - IOS-XE 17.x support
       [Source: Cisco Official Datasheet, confidence: 98%]"

User: "When does this equipment reach end-of-life?"
NEXO: "The C9200-24P has the following lifecycle dates:
       - End of Sale: 2027-06-30
       - End of Support: 2032-06-30
       [Source: Cisco Product Lifecycle Page]"

User: "Show me the manual for this switch"
NEXO: "Here's the configuration guide for C9200-24P:
       [Link to S3-stored PDF]"
```

---

## 4. Functional Requirements

### 4.1 Feature: Post-Import Enrichment Pipeline

**Description:** After NexoImportAgent completes inventory import to PostgreSQL, automatically trigger enrichment for each new/updated equipment record.

**User Stories:**
- Como IT Manager, quero que o sistema automaticamente enriqueça dados de equipamentos para que minha equipe tenha acesso imediato a especificações técnicas
- Como Técnico de TI, quero que o NEXO encontre manuais oficiais para que eu possa resolver problemas rapidamente

**Acceptance Criteria:**
- [ ] Enrichment triggers automatically within 5 minutes of import completion
- [ ] Each equipment item is researched using Tavily Search API
- [ ] Results are stored in S3 with standardized JSON schema
- [ ] Failed enrichments are queued for retry (max 3 attempts)
- [ ] Enrichment status is tracked in PostgreSQL metadata

**Technical Flow:**
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ NexoImportAgent │────▶│ PostgreSQL       │────▶│ EventBridge     │
│ (Import Done)   │     │ (Equipment Data) │     │ (Trigger)       │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ S3 (Knowledge   │◀────│ EnrichmentAgent  │◀────│ Tavily API      │
│ Repository)     │     │ (Strands)        │     │ (Search/Extract)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### 4.2 Feature: Multi-Source Data Aggregation

**Description:** For each equipment item, search multiple authoritative sources and aggregate information into a unified knowledge record.

**User Stories:**
- Como Inventory Manager, quero dados de múltiplas fontes oficiais para garantir precisão das informações
- Como Procurement, quero preços de diferentes vendors para comparação

**Data Sources (Priority Order):**

| Source Type | Examples | Data Retrieved |
|-------------|----------|----------------|
| **Vendor Official** | cisco.com, hp.com, dell.com | Specs, datasheets, lifecycle |
| **Documentation** | Vendor support portals | Manuals, guides, firmware |
| **Market Intelligence** | IT marketplaces | Pricing, availability |
| **Community Knowledge** | Reddit r/networking, forums | Compatibility issues, tips |

**Acceptance Criteria:**
- [ ] Search queries are optimized per equipment category (network, server, storage)
- [ ] Tavily `search_depth: advanced` used for comprehensive results
- [ ] Source quality is scored and tracked
- [ ] Data conflicts are flagged for human review
- [ ] Last enrichment date is tracked per equipment

### 4.3 Feature: S3 Knowledge Repository

**Description:** Store all enriched data in S3 with a structured schema optimized for RAG retrieval.

**User Stories:**
- Como Data Engineer, quero dados estruturados em S3 para facilitar criação do RAG
- Como IT Manager, quero histórico de enriquecimento para auditoria

**S3 Structure:**
```
s3://faiston-nexo-knowledge/
├── equipment/
│   ├── {serial_number}/
│   │   ├── metadata.json        # Core specs, lifecycle dates
│   │   ├── datasheet.pdf        # Official datasheet (if available)
│   │   ├── manual.pdf           # Configuration/user manual
│   │   ├── enrichment_log.json  # Enrichment history
│   │   └── raw_sources/         # Raw Tavily responses
│   │       ├── search_001.json
│   │       └── extract_001.json
├── part_numbers/
│   └── {part_number}/
│       └── aggregated_specs.json # Consolidated specs for model
└── vendors/
    └── {vendor_name}/
        └── product_catalog.json  # Vendor product mappings
```

**JSON Schema (metadata.json):**
```json
{
  "serial_number": "ABC123",
  "part_number": "C9200-24P-A",
  "vendor": "Cisco",
  "model": "Catalyst 9200-24P",
  "category": "network_switch",
  "specifications": {
    "ports": 24,
    "port_type": "1GbE PoE+",
    "poe_budget_watts": 370,
    "uplinks": "4x 10G SFP+",
    "storage": "128GB SSD"
  },
  "lifecycle": {
    "release_date": "2019-03-01",
    "end_of_sale": "2027-06-30",
    "end_of_support": "2032-06-30",
    "current_firmware": "17.12.1"
  },
  "documentation": {
    "datasheet_url": "s3://...",
    "manual_url": "s3://...",
    "quick_start_url": "https://..."
  },
  "market": {
    "msrp_usd": 4500,
    "street_price_usd": 3200,
    "price_updated": "2026-01-13"
  },
  "enrichment": {
    "last_updated": "2026-01-13T10:30:00Z",
    "sources_used": ["cisco.com", "cdw.com"],
    "confidence_score": 0.95
  }
}
```

**Acceptance Criteria:**
- [ ] S3 bucket created with appropriate IAM policies
- [ ] Versioning enabled for audit trail
- [ ] Lifecycle policies for cost optimization (Glacier after 1 year)
- [ ] Cross-region replication for disaster recovery
- [ ] Schema validation on write

### 4.4 Feature: Bedrock RAG Integration

**Description:** Create a Knowledge Base in Amazon Bedrock using the S3 knowledge repository, enabling NEXO Assistant to answer equipment questions with enriched data.

**User Stories:**
- Como usuário do NEXO, quero perguntar sobre equipamentos em linguagem natural
- Como IT Manager, quero que o NEXO cite fontes ao responder perguntas

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXO Assistant RAG Flow                      │
│                                                                 │
│  User Query ──▶ NEXO Assistant ──▶ Bedrock Knowledge Base       │
│       │              │                      │                   │
│       │              │                      ▼                   │
│       │              │            S3 Knowledge Repository       │
│       │              │                      │                   │
│       │              ◀──────────────────────┘                   │
│       │              │                                          │
│       ◀──────────────┘ (Response with citations)                │
└─────────────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Bedrock Knowledge Base created with S3 as data source
- [ ] Chunking strategy optimized for equipment specs
- [ ] Embedding model: Titan Embeddings V2
- [ ] NEXO Assistant uses RetrieveAndGenerate API
- [ ] Citations included in responses
- [ ] Knowledge Base syncs daily + on-demand after enrichment

### 4.5 Feature: Agent Integration (NexoImportAgent)

**Description:** Integrate Tavily tools into NexoImportAgent for on-demand enrichment during import process.

**User Stories:**
- Como sistema, quero enriquecer dados durante importação para maior eficiência
- Como usuário, quero que equipamentos novos já venham com informações completas

**Tavily Tools to Integrate:**

| Tool | Purpose | Usage in NEXO |
|------|---------|---------------|
| `tavily_search` | Web search optimized for LLMs | Find equipment specs, prices |
| `tavily_extract` | Content extraction from URLs | Get datasheets, manuals |
| `tavily_crawl` | Deep site crawling | Vendor product catalogs |

**Implementation:**
```python
# server/agentcore-inventory/agents/nexo_import/tools/tavily_enrichment.py
from strands_tools import tavily_search, tavily_extract

@tool
async def enrich_equipment(
    part_number: str,
    vendor: str,
    category: str
) -> EnrichmentResult:
    """
    Enrich equipment data using Tavily Search.

    Args:
        part_number: Equipment part number (e.g., C9200-24P)
        vendor: Manufacturer (e.g., Cisco)
        category: Equipment category (network, server, storage)

    Returns:
        EnrichmentResult with specs, lifecycle, documentation
    """
    # Search for official specs
    specs_query = f"{vendor} {part_number} specifications datasheet"
    specs_results = await tavily_search(
        query=specs_query,
        search_depth="advanced",
        include_domains=[f"{vendor.lower()}.com"],
        max_results=5
    )

    # Extract datasheet content
    if specs_results.get("datasheet_url"):
        datasheet = await tavily_extract(
            urls=[specs_results["datasheet_url"]]
        )

    return EnrichmentResult(
        specs=parse_specs(specs_results),
        datasheet=datasheet,
        confidence=calculate_confidence(specs_results)
    )
```

**Acceptance Criteria:**
- [ ] Tavily tools imported from `strands-agents-tools`
- [ ] API key stored in AWS Secrets Manager
- [ ] Rate limiting implemented (1000 requests/month on free tier)
- [ ] Fallback to cached data if Tavily unavailable
- [ ] Enrichment can be triggered manually via API

### 4.6 Feature: ValidationAgent Enhancement

**Description:** Use Tavily to validate part numbers and detect potential data entry errors during import.

**User Stories:**
- Como sistema, quero validar part numbers contra fontes oficiais
- Como Inventory Manager, quero alertas sobre part numbers inválidos

**Validation Flow:**
```
Part Number: C9200-24P-A
    │
    ▼
Tavily Search: "C9200-24P-A Cisco official part number"
    │
    ├── Found: ✓ Valid Cisco SKU
    │   └── Confidence: 98%
    │
    └── Not Found: ⚠️ Possible error
        └── Suggestions: C9200-24P-E, C9200-24P-L
```

**Acceptance Criteria:**
- [ ] Part number validation runs before import confirmation
- [ ] Invalid part numbers flagged to user with suggestions
- [ ] Validation results cached (24h TTL)
- [ ] Bulk validation supported (batch of 50)

### 4.7 Feature: LearningAgent Pattern Research

**Description:** Use Tavily to research common file formats and column naming patterns from public sources.

**User Stories:**
- Como LearningAgent, quero aprender padrões de arquivos de outros sistemas
- Como sistema, quero sugerir mapeamentos baseados em padrões da indústria

**Research Queries:**
- "Cisco inventory export CSV format columns"
- "standard IT asset management file format"
- "equipment inventory spreadsheet template columns"

**Acceptance Criteria:**
- [ ] Pattern research triggered for unknown file formats
- [ ] Results stored in AgentCore Memory (global namespace)
- [ ] Confidence-weighted learning (higher for official sources)

---

## 5. Technical Architecture

### 5.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    NEXO Tavily Enrichment Architecture                    │
│                                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────────┐ │
│  │ Frontend    │    │ API Gateway  │    │ faiston_inventory_orchestration    │ │
│  │ (Next.js)   │───▶│ (HTTP)       │───▶│ (Orchestrator)              │ │
│  └─────────────┘    └──────────────┘    └──────────────┬──────────────┘ │
│                                                         │                │
│                           ┌─────────────────────────────┼────────────┐   │
│                           │         A2A Protocol        │            │   │
│                           ▼                             ▼            ▼   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐      │
│  │ NexoImportAgent │  │ EnrichmentAgent  │  │ ValidationAgent    │      │
│  │ (Strands)       │  │ (NEW - Strands)  │  │ (Strands)          │      │
│  └────────┬────────┘  └────────┬─────────┘  └────────┬───────────┘      │
│           │                    │                      │                  │
│           │      ┌─────────────┴──────────────────────┘                  │
│           │      │                                                       │
│           ▼      ▼                                                       │
│  ┌─────────────────────────────┐    ┌──────────────────────────────┐    │
│  │ Tavily API                  │    │ AWS Services                  │    │
│  │ - tavily_search             │    │ - S3 (Knowledge Repository)   │    │
│  │ - tavily_extract            │    │ - Bedrock KB (RAG)            │    │
│  │ - tavily_crawl              │    │ - Secrets Manager (API Key)   │    │
│  └─────────────────────────────┘    │ - EventBridge (Triggers)      │    │
│                                     │ - Aurora PostgreSQL (Metadata)│    │
│                                     └──────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Technology Stack

**New Components:**

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Search API** | Tavily Search API | AI-optimized web search |
| **Agent Framework** | AWS Strands Agents | EnrichmentAgent implementation |
| **Knowledge Store** | Amazon S3 | Enriched data repository |
| **RAG Engine** | Amazon Bedrock KB | Knowledge Base for NEXO Assistant |
| **Secrets** | AWS Secrets Manager | Tavily API key storage |
| **Triggers** | Amazon EventBridge | Post-import enrichment events |

**Existing Components (Integration):**

| Component | Integration Point |
|-----------|-------------------|
| NexoImportAgent | Triggers enrichment post-import |
| ValidationAgent | Uses Tavily for part number validation |
| LearningAgent | Uses Tavily for pattern research |
| NEXO Assistant | Queries Bedrock KB for enriched data |
| Aurora PostgreSQL | Stores enrichment metadata |

### 5.3 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Enrichment Data Flow                            │
│                                                                         │
│  1. IMPORT COMPLETE                                                     │
│     NexoImportAgent ──▶ PostgreSQL (equipment data)                     │
│                     ──▶ EventBridge (ImportCompleted event)             │
│                                                                         │
│  2. ENRICHMENT TRIGGERED                                                │
│     EventBridge ──▶ EnrichmentAgent (Lambda)                            │
│                                                                         │
│  3. DATA RESEARCH                                                       │
│     EnrichmentAgent ──▶ Tavily API                                      │
│                     ├── tavily_search (specs, lifecycle)                │
│                     ├── tavily_extract (datasheets, manuals)            │
│                     └── tavily_crawl (vendor catalogs)                  │
│                                                                         │
│  4. DATA STORAGE                                                        │
│     EnrichmentAgent ──▶ S3 (structured JSON + documents)                │
│                     ──▶ PostgreSQL (enrichment_status, last_updated)    │
│                                                                         │
│  5. RAG SYNC                                                            │
│     S3 change ──▶ Bedrock KB sync (scheduled/on-demand)                 │
│                                                                         │
│  6. USER QUERY                                                          │
│     User ──▶ NEXO Assistant ──▶ Bedrock KB (RetrieveAndGenerate)        │
│          ◀── Response with citations ◀──                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.4 API Design

**EnrichmentAgent Tools:**

```python
# Tool: enrich_equipment
Input:
  - serial_number: str
  - part_number: str
  - vendor: str
  - category: str (network|server|storage|peripheral)
Output:
  - specifications: dict
  - lifecycle: dict
  - documentation: dict
  - market: dict
  - confidence_score: float

# Tool: validate_part_number
Input:
  - part_number: str
  - vendor: str (optional)
Output:
  - is_valid: bool
  - suggestions: list[str] (if invalid)
  - vendor_confirmed: str
  - confidence: float

# Tool: get_equipment_manual
Input:
  - part_number: str
  - manual_type: str (configuration|quickstart|installation)
Output:
  - manual_url: str
  - s3_path: str (if downloaded)
  - pages: int
```

**EventBridge Event Schema:**

```json
{
  "source": "nexo.import",
  "detail-type": "ImportCompleted",
  "detail": {
    "import_id": "uuid",
    "equipment_count": 150,
    "new_items": ["serial1", "serial2"],
    "updated_items": ["serial3"],
    "timestamp": "2026-01-13T10:00:00Z"
  }
}
```

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Requirement |
|--------|-------------|
| Enrichment latency | <30s per equipment item |
| Tavily API response | <5s per query |
| S3 write latency | <1s per document |
| RAG query latency | <3s end-to-end |
| Batch enrichment | 50 items/minute |

### 6.2 Scalability

| Dimension | Requirement |
|-----------|-------------|
| Monthly equipment imports | 10,000 items |
| Tavily API calls | 1,000/month (free tier) → upgrade as needed |
| S3 storage | 100GB Year 1, 500GB Year 3 |
| Concurrent enrichments | 10 parallel |

### 6.3 Security

| Requirement | Implementation |
|-------------|----------------|
| API key protection | AWS Secrets Manager |
| S3 encryption | SSE-S3 (AES-256) |
| Access control | IAM roles per agent |
| Data classification | Equipment specs = Internal |
| Audit logging | CloudTrail + S3 access logs |

### 6.4 Reliability

| Metric | Target |
|--------|--------|
| Enrichment success rate | ≥95% |
| System availability | 99.9% |
| Data durability | 99.999999999% (S3) |
| Retry policy | 3 attempts with exponential backoff |

### 6.5 Observability

| Component | Monitoring |
|-----------|------------|
| EnrichmentAgent | X-Ray traces, CloudWatch metrics |
| Tavily API | Request count, latency, errors |
| S3 | Object count, storage size, access patterns |
| Bedrock KB | Query count, latency, relevance scores |

---

## 7. Deployment & CI/CD

### 7.1 Deployment Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    Enrichment Module Deployment                  │
│                                                                 │
│  1. Code Push ──▶ GitHub Actions                                │
│                                                                 │
│  2. Terraform Plan ──▶ Review ──▶ Apply                         │
│     - S3 bucket                                                 │
│     - Secrets Manager secret                                    │
│     - EventBridge rule                                          │
│     - Bedrock Knowledge Base                                    │
│                                                                 │
│  3. AgentCore Deploy ──▶ EnrichmentAgent                        │
│                                                                 │
│  4. Integration Test ──▶ Smoke Test                             │
│     - Enrich 1 test equipment                                   │
│     - Verify S3 storage                                         │
│     - Query RAG                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Environment Strategy

| Environment | Purpose | Tavily Tier |
|-------------|---------|-------------|
| Development | Local testing | Free (1000/month) |
| Staging | Integration testing | Free (shared) |
| Production | Live system | Paid (as needed) |

---

## 8. Roadmap

### Phase 1: Foundation (Week 1-2)

- [ ] Create S3 bucket with proper structure
- [ ] Configure Secrets Manager for Tavily API key
- [ ] Implement basic `enrich_equipment` tool
- [ ] Test with 10 sample equipment items
- [ ] Create Terraform resources

### Phase 2: Agent Integration (Week 3-4)

- [ ] Create EnrichmentAgent (Strands)
- [ ] Integrate with NexoImportAgent via EventBridge
- [ ] Implement `validate_part_number` tool
- [ ] Add enrichment to import workflow
- [ ] Implement retry logic and error handling

### Phase 3: RAG Setup (Week 5-6)

- [ ] Create Bedrock Knowledge Base
- [ ] Configure S3 as data source
- [ ] Optimize chunking strategy
- [ ] Integrate with NEXO Assistant
- [ ] Test query accuracy

### Phase 4: Production (Week 7-8)

- [ ] Performance optimization
- [ ] Monitoring dashboards
- [ ] Documentation
- [ ] User training
- [ ] Go-live

---

## 9. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Tavily rate limits | High | Medium | Implement caching, queue management |
| Data quality from web | Medium | Medium | Multi-source validation, confidence scoring |
| Vendor site changes | Low | High | Fallback to cached data, monitoring |
| Cost overrun | Medium | Low | Usage monitoring, alerts at 80% budget |
| API key exposure | Critical | Low | Secrets Manager, IAM least privilege |

---

## 10. Appendix

### A. Tavily API Reference

- **Pricing:** Free tier 1000 requests/month, Paid tiers available
- **Rate Limits:** 100 requests/minute
- **Documentation:** https://docs.tavily.com/
- **Strands Integration:** `from strands_tools import tavily_search`

### B. Equipment Categories

| Category | Vendors | Example Part Numbers |
|----------|---------|---------------------|
| Network Switches | Cisco, Juniper, Arista | C9200-24P, EX4300-48P |
| Routers | Cisco, Juniper | ISR4331, MX240 |
| Servers | Dell, HP, Lenovo | R740, DL380, SR650 |
| Storage | NetApp, EMC, Pure | FAS8700, Unity 380 |
| Wireless | Cisco, Aruba, Ubiquiti | C9120AXI, AP-505 |

### C. Sample Tavily Queries

```python
# Specification search
tavily_search(
    query="Cisco C9200-24P specifications datasheet",
    search_depth="advanced",
    include_domains=["cisco.com"],
    max_results=5
)

# Lifecycle search
tavily_search(
    query="Cisco C9200-24P end of life end of support dates",
    search_depth="advanced",
    include_domains=["cisco.com"],
    max_results=3
)

# Manual extraction
tavily_extract(
    urls=["https://cisco.com/c/en/us/products/collateral/switches/catalyst-9200-series-switches/datasheet.pdf"]
)
```

---

**Document Status:** Draft
**Next Review:** 2026-01-20
**Approval Required:** Fabio Santos (Product Owner), Tech Lead
