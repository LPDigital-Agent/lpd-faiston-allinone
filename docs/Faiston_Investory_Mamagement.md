Faiston Inventory Management: A Developer's Guide from Manual Operations to Autonomous AI Agents

Introduction: The Strategic Vision for Faiston's Logistics

Inventory management is a critical strategic function at Faiston, directly impacting operational efficiency, customer satisfaction, and financial performance. This document provides a comprehensive overview for software developers tasked with building our next-generation logistics platform. It details the evolution of our operations from the current, human-driven model ("As Is") to a future-state, autonomous system powered by a sophisticated network of AI agents ("To Be").

The primary goal of this guide is to explain the 'what' and 'why' behind the system's features and its ambitious vision. By providing the essential business and operational context, we aim to empower you to not just write code, but to architect solutions that solve real-world challenges and anticipate future needs. This transformation is designed to shift Faiston's logistics from a reactive cost center into a proactive, predictive, and value-generating asset that serves as a core competitive differentiator.


--------------------------------------------------------------------------------


1. The Current State ("As Is"): A Human-Driven Ecosystem

To build the future system, it is essential to first understand the complexities, manual processes, and existing tools of the current operational landscape. This section details the real-world workflows that the new architecture will automate and enhance, providing a clear picture of the challenges we are addressing. The processes described below are the direct inputs that have shaped the design of our future-state system.

1.1. Core Inventory Control: A Multi-System Manual Process

Core inventory management—including stock entries, exits, and transfers—is currently a highly manual process distributed across multiple systems and documents. The stock entry ("internalização") process, in particular, highlights the operational overhead and risk.

* Initiation: The process begins upon receiving a Fiscal Note (NF), either via email or with a physical delivery of goods.
* Manual Inventory: Logistics personnel manually inventory the arriving items, capturing the Part Number and Serial Number.
* Project Validation: If a project ID is not associated with the items, the team must manually request validation from the Finance team. This inter-departmental dependency is a critical bottleneck that introduces significant latency into the stock entry process.
* SAP Data Entry: Merchandise data is manually entered into SAP. This includes the item number, quantity, price, and the correct warehouse code (e.g., 01 – Recebimento for Faiston-owned equipment, 05 – Itens de terceiros for third-party items). Serial numbers are also entered manually in a separate SAP module.
* SGA Data Entry: The entire entry process is then duplicated in the SGA system, where items are linked to the Fiscal Note, project, and end-client. This dual-entry process is not just inefficient; it's a primary source of data integrity errors that lead to inventory discrepancies and fiscal reconciliation issues.
* Spreadsheet Reliance: The entire process is supported and tracked by multiple, disparate spreadsheets, creating data silos and reconciliation challenges.

It is important to note that the current stock hierarchy is not physical (e.g., shelf, position) but logical, organized primarily by the project ID associated with the equipment.

1.2. Expedition Workflow: Manual Decision-Making and Execution

The current expedition process is a multi-step workflow initiated by a request (chamado) from an operational team in Tiflux. It relies heavily on manual intervention and decision-making at nearly every stage.

1. Staging: Upon receiving a ticket, the logistics team manually identifies the required equipment and its associated project, physically verifies stock availability, and separates the item for dispatch.
2. Carrier Quotation: The team manually requests quotes from various carriers. This is done via email (for transportadoras), a mobile app (Loggi), or a carrier website (Gollog). The only exception is Correios, where the VIPP tool is used.
3. Carrier Selection: Based on the quotes received, the team manually selects the best carrier. The guiding criteria for this decision are "menor custo e menor prazo" (lowest cost and shortest timeframe). This manual decision is subjective, lacks historical data for validation, and cannot adapt in real-time to carrier performance issues, making it operationally fragile.
4. Packaging & Fiscal Note: The equipment is packed, and the Fiscal Note is manually issued in SAP. This final step requires the team to select the client, item, quantity, and warehouse, and fill in all necessary tax and transport details.

1.3. Reverse Logistics: A Tool-Assisted but Manual Workflow

While the reverse logistics process for returns utilizes the VIPP online tool for Correios, it remains fundamentally dependent on manual tracking and direct communication, creating significant overhead.

* A postage code is generated for the technician in the VIPP system.
* All subsequent communication with the technician regarding the return, including instructions and follow-ups, is handled manually via WhatsApp.
* The progress of the return shipment is tracked manually in a dedicated spreadsheet ("planilha").
* Confirmation of receipt is a fragmented, multi-team handoff. The logistics team tracks the delivery on the carrier's website. Upon confirmed arrival, they inform the Gestão de Ativos (Asset Management) team of the serial number, who then validates the physical arrival. Finally, the Gestão de Incidentes (Incident Management) team performs the final takedown in their controls. This workflow creates multiple points of failure and delays.

If a technician fails to post a return item within the designated timeframe, the team manually generates a new postage code or escalates the issue to the "Rede Credenciada" for support.

1.4. Tracking and Monitoring: Fragmented and Reactive

The current tracking and monitoring process is reactive and fragmented, relying on manual checks across various carrier platforms and basic communication tools.

* Status Checks: Status updates are performed by manually visiting carrier websites (Correios, Gollog, Loggi) or by communicating via email and WhatsApp with other transport companies.
* Frequency: These checks are typically conducted once in the morning and once in the afternoon ("Manhã e a tarde"). This twice-daily manual check means that for hours at a time, Faiston has no real-time visibility into shipment status, making the entire monitoring process reactive by design. Problems are discovered long after they occur.
* Reporting: Performance dashboards and tracking reports are created and maintained manually in Excel.
* Alerting: Alerts for delays or other issues are communicated manually through system messages in Tiflux and direct messages on WhatsApp.

The inefficiencies, data fragmentation, and operational risks described in this section are the primary drivers for the new AI-powered vision detailed next.


--------------------------------------------------------------------------------


2. The Future Vision ("To Be"): An Autonomous, AI-Driven System

The "To Be" vision represents a strategic shift from the manual, reactive state to a proactive, intelligent, and autonomous logistics operation. This vision is enabled by an **AI-First, Agentic architecture** built entirely on AWS infrastructure, where intelligent AI agents (powered by AWS Strands Agents Framework + Gemini 3.0 LLM) observe, reason, decide, and act autonomously on behalf of the logistics team.

> **Implementation Note:** The agents described in sections 2.2-2.4 represent the future roadmap and vision. The current implementation consists of **14 specialized agents** documented in [AGENT_CATALOG.md](AGENT_CATALOG.md), which form the foundation for this vision. Agent names and descriptions below reflect future-state planning.

2.1. The Architectural Foundation: AI-First on AWS

The core architectural principle is an **AI-First, Agentic architecture** built entirely on AWS infrastructure, leveraging Google's Gemini 3.0 LLM family via API for advanced reasoning capabilities.

**Current Technology Stack (Mandatory per CLAUDE.md)**

| Component | Technology |
|-----------|------------|
| **Agent Framework** | AWS Strands Agents + Google ADK v1.0 |
| **LLM** | Gemini 3.0 Family (Pro with Thinking for critical agents, Flash for operational agents) |
| **Agent Runtime** | AWS Bedrock AgentCore |
| **Primary Datastore** | Aurora PostgreSQL (inventory data) |
| **Secondary Datastore** | DynamoDB (HIL tasks, audit logs, sessions) |
| **Inter-Agent Protocol** | A2A (Agent-to-Agent) - JSON-RPC 2.0 on port 9000 |
| **Event System** | AWS EventBridge |
| **Infrastructure** | 100% AWS (no Google Cloud Platform services) |

> **Note:** See [ADR-003](architecture/ADR-003-gemini-model-selection.md) for LLM model selection rationale.
> See [AGENT_CATALOG.md](AGENT_CATALOG.md) for the complete list of 14 implemented agents.

**Key Architectural Principles:**
- **AI-First**: Agents are the primary execution model, not traditional microservices
- **AWS Strands Agents Framework**: All agents built using AWS Strands + Google ADK
- **Agent-to-Agent (A2A) Communication**: Inter-agent communication via A2A protocol (JSON-RPC 2.0)
- **Event-Driven**: AWS EventBridge for asynchronous event orchestration
- **Memory-Aware**: Agents use AWS Bedrock AgentCore Memory (Session, STM, LTM)
- **Gemini API Integration**: Google's Gemini 3.0 LLM accessed via API (not GCP infrastructure)

2.2. Autonomous Core Operations and Logistics Execution

The future system will automate the entire lifecycle of an inventory item, from entry to dispatch, using a team of specialized AI agents that work together to execute complex workflows.

Automated Inventory Control (Stock Reconciliation Agent) This agent completely eliminates manual data entry in SGA and SAP for inventory movements. It functions by observing system events, such as expeditions and confirmed returns, and automatically executing the corresponding +/− movements in the inventory database. This ensures the inventory record is always synchronized in real-time, directly replacing the error-prone, manual dual-entry into SAP and SGA and eliminating a major source of inventory inaccuracy.

Intelligent Dispatch (Dispatch Orchestrator Agent) Acting as the system's "control tower," this agent monitors for new tickets in Tiflux, autonomously decides the correct logistical action (e.g., expedite, transfer, reverse), and triggers the appropriate AWS microservices to execute the task. This removes subjective human decision-making and the associated operational fragility from the standard workflow, dramatically increasing speed and consistency.

Automated Tracking (Tracking Agent) In stark contrast to the twice-daily manual checks of the current process, this agent will automatically and continuously query carrier APIs to retrieve real-time status updates, such as "Postado," "Em trânsito," "Entregue," "Ocorrência," and the critical "RETIDO_FISCAL" status. This provides constant, real-time visibility into every shipment.

Proactive SLA Management (SLA Monitor Agent) Working in concert with the Tracking Agent, this agent's purpose is to move from reactive problem-solving to proactive intervention. It compares real-time tracking data against contractual SLAs and uses predictive models to identify potential violations before they occur, allowing the system or human teams to take corrective action. This directly addresses the reactive nature of the current manual alerting process.

2.3. Predictive Intelligence and Operational Optimization

The system will move beyond simple automation to prediction, enabling Faiston to anticipate future needs, optimize resource allocation, and identify systemic problems for continuous improvement.

Demand Forecasting (Demand Forecast Agent) This agent analyzes historical consumption and equipment failure data to predict future demand for specific parts by region. The value is immense: it allows for proactive stock replenishment, preventing stockouts and directly helping to reduce costs of emergency air transport ("reduzir custos de transporte aéreo emergencial").

Reverse Logistics Prediction (Reverse Prediction Agent) By analyzing asset usage patterns, failure rates, and technician history, this agent predicts which assets are most likely to require a return. This allows for optimized collection planning, improving efficiency and reducing the cycle time for asset recovery, moving beyond the current system's complete lack of foresight.

Automated Root-Cause Analysis (Root-Cause Analysis Agent) This powerful LLM-based agent reviews historical tickets and logistics data to identify recurring problems that are invisible to human operators. For example, it can flag a specific carrier that consistently causes delays in a certain region or a technician who is frequently associated with returns, providing actionable insights for process improvement and supplier management.

2.4. Enhanced System and User Interaction

The future system will fundamentally transform how both internal logistics teams and external field technicians interact with logistics data and processes, making interactions more intuitive, efficient, and intelligent.

* Conversational Data Access (Sasha Logística Chat): This agent provides a natural language chat interface for the logistics team. Instead of running complex reports or searching through spreadsheets, users can simply ask questions like, "How many switches are in the Rio base?" or "Which returns are pending for more than 5 days?" to get instant, accurate answers, eliminating dependence on Excel.
* Automated Technician Communication (WhatsApp / Logística Agent): This agent automates all routine communication with field technicians via the WhatsApp Cloud API. It will proactively send dispatch notifications, tracking codes, and return instructions, as well as receive confirmations. This eliminates the manual, error-prone WhatsApp communication and spreadsheet tracking that define the current reverse logistics process.
* Intelligent Ticket Triage (AutoTagging Agent): Using natural language understanding, this agent will automatically read and classify incoming Tiflux tickets (e.g., expedição, reversa, reposição). This speeds up initial processing, reduces human categorization errors, and ensures tickets are routed correctly from the moment they are created.

This network of specialized agents collaborates to create a self-managing and self-optimizing logistics system, transforming the operational backbone of Faiston.


--------------------------------------------------------------------------------


3. Bridging the Gap: From "As Is" to "To Be"

This document has journeyed from a manual, fragmented present to an automated, intelligent future. This final section is designed for you, the developer, to highlight the key conceptual shifts you will be responsible for building into the system's foundation. Your work on the transactional core is what will enable the intelligence layer to function.

3.1. Key Transformations for the Developer to Enable

The following table directly contrasts the current and future states for key functions and clarifies your mission in building the bridge between them.

Feature Area	From: "As Is" (Human-Driven)	To: "To Be" (Agent-Driven)	The Developer's Mission
Stock Entry	Manual, dual-system entry in SAP and SGA based on emails and NFs.	Stock Reconciliation Agent (see reconciliacao agent in AGENT_CATALOG) automatically processes Stock.Updated events to adjust inventory.	Build agents using AWS Strands framework with tools/capabilities for inventory operations. Agents observe EventBridge events, reason using Gemini 3.0, and execute via MCP tools (Aurora PostgreSQL updates). NOT traditional REST microservices.
Carrier Selection	Manual process of emailing/calling carriers for quotes and selecting based on cost/time.	Dispatch Orchestrator Agent (see expedition agent in AGENT_CATALOG) makes optimal choices based on reasoning and real-time data.	Implement agent tools (MCP) that abstract carrier APIs (BestLog, Gollog, etc.). Agent uses Gemini 3.0 reasoning to evaluate options and A2A protocol to coordinate with other agents.
Shipment Tracking	Manual checks on carrier websites, twice daily. Data is copied to Excel.	Tracking Agent (see carrier agent in AGENT_CATALOG) polls APIs continuously and publishes Tracking.StatusChanged events.	Build agent with carrier API integration tools, event publishing capabilities via EventBridge, and AgentCore Memory to track shipment state. Agent uses A2A to notify other agents of status changes.
SLA Monitoring	Reactive alerts in Tiflux or WhatsApp after a problem has occurred.	SLA Monitor Agent (future - see compliance agent in AGENT_CATALOG for current implementation) proactively predicts and alerts on potential SLA violations.	Build agents that consume EventBridge events, use Gemini 3.0 reasoning to analyze patterns, leverage AgentCore LTM for historical context, and emit alerts via A2A to coordination agents.

3.2. Conclusion: Building the Foundation for Intelligence

As a developer on this project, your primary role is to construct **intelligent, autonomous AI agents** using the AWS Strands Agents Framework. These agents are **not traditional microservices**—they are cognitive entities that reason, learn, and make decisions using the Gemini 3.0 LLM.

**Key Development Principles:**
- **AI-First Architecture**: Design agent capabilities, not REST endpoints
- **Agent-to-Agent (A2A) Communication**: Agents collaborate via A2A protocol, not direct API calls
- **Event-Driven**: Agents observe and emit events via AWS EventBridge
- **Memory-Aware**: Leverage AWS Bedrock AgentCore Memory (Session, STM, LTM) for context retention
- **Tool-Based Execution**: Agents use tools (MCP, AWS services) to interact with external systems
- **AWS Strands Framework**: All agents built using AWS Strands + Google ADK v1.0

The current implementation features **14 specialized agents** (see [AGENT_CATALOG.md](AGENT_CATALOG.md)) that form the foundation for the autonomous logistics vision described in this document.

---

## References

- [AGENT_CATALOG.md](AGENT_CATALOG.md) - Complete list of 14 SGA agents (current implementation)
- [ADR-003](architecture/ADR-003-gemini-model-selection.md) - Gemini 3.0 model selection rationale
- [SGA_ESTOQUE_ARCHITECTURE.md](architecture/SGA_ESTOQUE_ARCHITECTURE.md) - Technical architecture documentation
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database design (Aurora PostgreSQL + DynamoDB)
- [AWS Strands Agents Documentation](https://strandsagents.com/latest/) - Official framework documentation
- [Agent-to-Agent (A2A) Protocol](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/) - Inter-agent communication
