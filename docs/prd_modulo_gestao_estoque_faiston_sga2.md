# PRD — SGA 2.0 (Faiston)
## Module 2: Inventory Management (+/–) — AI-First, Autonomous (Observe → Think → Learn → Execute)

**Status:** Draft (v0.1)
**Product:** Faiston SGA 2.0
**Module:** Inventory Management (+/–) — operational *core*
**Owner:** Product (LPDigital)
**Stakeholders:** Logistics (Bruna), Operations (Rodrigo), Finance/Tax, Field Technicians, Management (Executive Board), IT/Security

---

## 1) Executive Summary

The Inventory Management Module is the "heart" of SGA 2.0: it maintains the **single source of truth** about **where each asset is**, **what the balance is** by **base/technician/project**, and **what movements** occurred (inbound, outbound, transfer, reverse, adjustments).

The SGA 2.0 refactoring changes the paradigm:

- Out with the "spreadsheet + ticket bridge" mode.
- In with an **autonomous engine** (AI-First) that:
  1) **Observes** events (tickets, shipments, returns, invoices, technician confirmations, inventories);
  2) **Thinks** (plans the correct flow and identifies inconsistencies);
  3) **Learns** (adjusts rules, extractions, and predictions with real feedback);
  4) **Executes** (updates balances, creates tasks, requests approvals, notifies people, and maintains audit trail).

The module must be designed to operate with **distributed inventory** (logistics center, bases, self storage, "advanced stock" with technicians and service storages), with tracking by **Part Number** and, when applicable, **Serial Number/RFID**, and with strict governance (Human-in-the-Loop) at risk points.

---

## 2) Problem and Context

Today the "+ / –" control and inventory visibility do not sustain end-to-end, mainly due to:

- Distributed inventory (bases + technicians + storage) with manual and fragmented control.
- Difficulty answering simple questions in real-time: "how many switches exist?", "where are they?", "how many in transit?", "how many in reverse?".
- Movements and decisions depend on individual *expertise* and manual message exchanges.
- Goods receipt depends on tax process (Invoice/SAP) and then "mirrors" something in SGA — with risk of divergence and rework.
- The ticket (Tiflux) is the real operational trigger, but inventory doesn't "close the loop" automatically.

SGA 2.0 needs to make inventory **auditable, live, and self-correcting**.

---

## 3) Product Objectives (and How to Measure)

### 3.1 Objectives (O)

**O1.** Make distributed inventory "queryable" and reliable in real-time (single source of truth).
**O2.** Drastically reduce manual work (spreadsheets, repeated checks, queries across multiple screens).
**O3.** Ensure end-to-end traceability per asset (from receipt to dispatch, installation, and reverse).
**O4.** Allow safe operation with autonomy (agents execute, humans approve when necessary).
**O5.** Prepare database and events for dispatch, tracking, reverse, and tax to operate "plug-and-play".

### 3.2 Suggested KPIs (K)

- **Inventory accuracy:** divergence ≤ 2% (global and per base).
- **Time to locate an item (serial or PN):** P50 ≤ 30s, P90 ≤ 2 min.
- **% of movements recorded automatically** (without manual entry): incremental target per phase.
- **Reduction in manual inventories** (quantity and time spent).
- **Exception rate per 1,000 movements** (items without serial, duplicates, "missing", etc.).
- **Update time per movement** (from evidence → updated balance).
- **% of movements with attached evidence** (Invoice, receipt, tracking, technician confirmation, photo).

---

## 4) Module Principles (AI-First + Safety)

### 4.1 Autonomy by Levels (important for governance)

- **Level A — Suggests:** the agent recommends; human confirms.
- **Level B — Executes with review:** the agent executes and places in review queue (short deadline).
- **Level C — Executes autonomously:** allowed only when:
  - risk is low,
  - evidence is strong,
  - and there is simple rollback.

### 4.2 "Evidence before action"

Every movement must have:
- **Minimum evidence** (e.g., Invoice, receipt, tracking, receipt photo, technician confirmation, inventory checklist).
- **Audit trail** (who/which agent did it, when, for what reason, with what data).

### 4.3 Mandatory Human-in-the-Loop

Mandatory for:
- High-value / high-risk movements.
- Transfer between projects/contracts when there are contractual restrictions.
- Inventory adjustments (difference between physical and system).
- Write-off/Disposal (BAD → Disposal) and losses/missing.
- Creation/modification of Part Number when it impacts tax/contracts.

---

## 5) Scope

### 5.1 Within Scope (Module MVP)

1. Item registration and catalog (Part Number) with rules for serial control and mandatory reverse.
2. Asset registration and tracking (serial, RFID, asset tag).
3. "Inventory locations" structure (bases, technicians, storage, DC) and balance per location.
4. Movements (+/–): inbound, outbound, transfer, reservation, reverse (inbound/outbound), and adjustment.
5. Conceptual integration with tickets: movement ↔ ticket linkage (parent/child) and "project".
6. AI-First mode:
   - invoice reading by voice/document,
   - automatic balance update when evidence exists,
   - divergence detection and task creation.
7. Inventory/cycle count with AI-assisted reconciliation.
8. Permissions, logs, and module audit trails (even if complete "Admin" is in another module).

### 5.2 Out of Scope (in this PRD)

- Complete dispatch modeling (quote, label, advanced picking/packing) — only what inventory needs to reserve/withdraw.
- Automated tracking by carrier — only tracking code linkage to movement.
- Complete tax/accounting — here we focus on "data that tax needs".
- GeoDispatch and technician route optimization — only treat "technician as inventory location".

### 5.3 Future (to keep track)

- Predictive optimization: demand forecast by base/technician and auto-replenishment.
- Fraud/anomaly detection (advanced compliance).
- "What-if" inventory simulation by contract and SLA.

---

## 6) Personas and Needs

### 6.1 Logistics (Inventory Operations)

- Needs to know quickly **where it is** and **how many exist**.
- Needs to register inbound/outbound with minimum friction.
- Needs an "inbox" of tasks and pending items that the system generates.

### 6.2 Operations (Ticket Management)

- Needs to request dispatch/reverse with complete data.
- Needs availability visibility before engaging logistics.

### 6.3 Field Technician (Advanced Stock)

- Needs to confirm receipt/use/return with few clicks/WhatsApp.
- Needs visibility of "their" inventory and what is pending reverse.

### 6.4 Finance/Tax

- Needs consistency between operational inventory and tax records.
- Needs traceability and auditable reports (Invoice ↔ movements ↔ assets).

### 6.5 Management / Executive

- Needs KPIs: accuracy, losses, logistics cost, efficiency, SLA, and trends.

---

## 7) Glossary (Domain Terms)

- **Project:** operational unit that, in practice, functions as "client/contract" within SGA.
- **End client:** the client served within a project.
- **Part Number (PN):** item registration (model/type) — may or may not require serial.
- **Serial Number:** individual asset identifier.
- **RFID / Asset Tag:** additional physical identifiers.
- **Location (Base):** any place where inventory can "exist" (DC, technical base, self storage, service storage, technician's home).
- **Warehouse/Tax Status:** inventory classification by type/ownership/condition (e.g., Receiving, BAD, Third-party items).
- **Movement:** event that changes (or reserves) balance at a location and records traceability.
- **Reservation:** sets aside balance for a ticket before dispatch.
- **Staging:** physical separation for dispatch (preparation area).
- **Reverse:** process of returning/bringing back the asset to inventory.

---

## 8) Domain Model (What Exists in the Module)

> This is not a technical database document; it's the product's "mental map".

### 8.1 Essential Entities

1. **Item (Part Number)**
   - name/description, group/category
   - serial control? (yes/no)
   - mandatory reverse? (yes/no)
   - required attributes by type (e.g., voltage, version, compatibility)

2. **Asset**
   - PN
   - serial (if applicable)
   - RFID/tag (optional)
   - condition: new / used / BAD / disposal / quarantine / under maintenance
   - ownership: Faiston / third-party (client) / partner
   - associated project/end client (when applicable)
   - history (timeline)

3. **Inventory Location**
   - type: Logistics Center, Technical Base, Self Storage, Service Storage, Technician
   - capacity/limitations (optional)
   - policies (e.g., "cannot receive third-party", "advanced stock only", etc.)

4. **Stock Balance**
   - by PN and/or by asset (serial)
   - by location
   - by condition (normal, BAD, etc.)
   - available vs reserved vs in transit (status)

5. **Stock Movement**
   - type: inbound / outbound / transfer / reverse / adjustment / reservation / cancellation
   - origin and destination (when applicable)
   - linkage with ticket (parent/child) and project
   - attached evidence (Invoice, receipt, photo, etc.)
   - author (human or agent) + "autonomy level"
   - system confidence (score) + justification

6. **Document**
   - Invoice, DANFE, XML (when exists), receipt, checklist, photo
   - AI-extracted metadata (PN, serial, quantities, values)

---

## 9) Inventory States and Rules

### 9.1 Asset States (serialized)

- **IN_STOCK (Available)**
- **RESERVED**
- **IN_STAGING**
- **IN_TRANSIT**
- **IN_USE (with technician / at client)**
- **AWAITING_REVERSE**
- **IN_REVERSE (posted/collected)**
- **UNDER_MAINTENANCE**
- **BAD**
- **QUARANTINE (awaiting inspection)**
- **DISPOSAL**
- **MISSING (only with approval and evidence)**

### 9.2 Movement Types (minimum viable)

- **Internalization (Inbound):** Invoice/receipt → inventory
- **Dispatch (Outbound):** inventory → technician/base/client
- **Transfer:** base A → base B (or technician ↔ base)
- **Reverse:** return → inventory (with or without sorting)
- **Adjustment:** corrections by inventory/audit (always with approval)
- **Reservation/Unreservation:** temporary block for service

---

## 10) Main Journeys (End-to-End)

### Journey A — Goods Receipt (Internalization)

**Typical Triggers**
- Invoice arrival by email / document delivered with equipment.
- Equipment arrival without notice (system must support).

**Expected Result**
- Assets registered (PN/serial), balance updated, and evidence attached.
- If critical data missing (ID/project), create task and block progress.

**Flow (High Level)**
1. User informs "Invoice/equipment arrived" in portal *or* forwards Invoice to monitored channel.
2. **Intake Agent** reads Invoice (document/voice), extracts PN, serial, RFID, quantity, values, and suggests project/end client.
3. **Inventory Agent** validates:
   - PN exists? if not, opens "PN registration task".
   - duplicate serial? if yes, opens exception.
   - project/ID exists? if not, requests registration/validation.
4. **Human-in-the-Loop** validates mandatory points (configurable by risk/confidence).
5. System records inbound and updates balance.
6. System records "data quality" (confidence, evidence) for future audit.

**Acceptance Criteria**
- Inbound supports serialized and non-serialized items.
- System prevents inbound "without project" when rule requires.
- Each inbound generates movement with evidence and audit trail.

---

### Journey B — Availability and Location Query (the "Inventory Google")

**Typical Trigger**
- Operations wants to know if part exists to serve ticket.
- Logistics needs to locate where item is and who has it.

**Expected Result**
- Search by PN/serial returns: balance by location, state, and recommendations.

**Essential UX**
- Unified search by:
  - PN (description, model, category),
  - serial/RFID/tag,
  - project/end client,
  - location/base/technician.

**Acceptance Criteria**
- Return shows "where" and "status" (available/reserved/in transit/…).
- Return shows evidence and history (to avoid "operational hallucination").

---

### Journey C — Reservation and Staging (Pre-Dispatch)

**Typical Triggers**
- Logistics child ticket requests item (e.g., AP, server, switch).
- Operations creates part need and system must reserve.

**Expected Result**
- Item reserved and "ready to stage", avoiding "two people taking the same".

**Flow (High Level)**
1. Request arrives linked to ticket (with PN or requirements).
2. **Allocation Agent** recommends:
   - best origin location (cost/deadline),
   - alternative if not available at preferred location.
3. System creates balance **reservation** (or specific serial).
4. Generates **pick list** and task for logistics.
5. Upon confirming staging, changes status to staging.

**Acceptance Criteria**
- Reservation blocks duplication.
- Ticket cancellation undoes reservation with trail.

---

### Journey D — Transfer Between Bases and/or Technicians

**Typical Triggers**
- Advanced stock replenishment.
- Reallocation due to demand change.
- Get item "closer" to incident (when applicable).

**Important Rules**
- Transfer between projects/contracts may require approval (policy).
- Every transfer must maintain traceability.

**Acceptance Criteria**
- Transfer changes balances correctly.
- Approval rules are respected (HIL).

---

### Journey E — Reverse (Asset Return)

**Typical Triggers**
- Installation generated BAD and needs to return.
- Equipment replacement.
- End of use / return of third-party equipment.

**Expected Result**
- System knows "what should return", "what returned", and updates balance/condition.

**Flow (High Level)**
1. Ticket / rule defines mandatory reverse.
2. System creates pending: "asset X needs to return".
3. Technician confirms status (WhatsApp/app) and posts/collects.
4. Upon receipt, logistics does sorting (condition) and updates state.
5. Divergences become exceptions (e.g., different serial, missing item).

**Acceptance Criteria**
- Reverse creates and closes the cycle in inventory with traceability.

---

### Journey F — Inventory and Audit (AI-Assisted Cycle Count)

**Typical Triggers**
- Monthly cycle, contractual audit, or divergence detected by AI.

**Expected Result**
- System proposes count, identifies divergences, and suggests adjustments (with HIL).

**Flow (High Level)**
1. System suggests a "count route" by risk/value/activity.
2. User records count (mobile/portal) and attaches evidence (photos).
3. **Reconciliation Agent** compares:
   - expected vs counted balance,
   - historical patterns,
   - possible causes (entry error, dispatch without withdrawal, missing).
4. System generates adjustment proposal + justification + risk.
5. Human approves or rejects.

**Acceptance Criteria**
- Adjustment does not occur without approval.
- Divergences remain traceable with probable cause.

---

## 11) Functional Requirements (Detailed)

### FR-01 — Part Number (PN) Registration

**Description**
Allow creation and maintenance of item catalog (PN) with minimum attributes and control rules.

**Minimum Fields**
- Type (product), group/category (if applicable)
- Serial control (yes/no)
- Mandatory reverse (yes/no)
- Name/description and tags

**Rules**
- If "serial control = yes", system requires serial on inbound and outbound.
- PN can have configurable "required attributes" (by client/project).

**Acceptance Criteria**
- Does not allow moving serialized item without serial.
- PN change log (who changed, before/after).

---

### FR-02 — Asset Registration and Tracking (Serialized)

**Description**
Allow individual asset registration with serial and history.

**Rules**
- Serial must be unique per PN (or global, according to rule).
- Alternative identifiers (RFID/tag) may exist, but serial dominates.

**Acceptance Criteria**
- Search by serial returns asset "timeline".
- Serial movements automatically update its state.

---

### FR-03 — Location Structure (Bases, Technicians, Storage)

**Description**
Register locations and treat them as inventory nodes.

**Supported Types**
- Logistics Center
- Technical Base
- Self Storage
- Service Storage (location with "key" and controlled access)
- Technician (individual advanced stock)

**Rules**
- Location can be associated with a project/client (when there is segregation).
- Location can have policies: "can receive third-party", "BAD only", etc.

**Acceptance Criteria**
- Query shows balance by location and by type.
- Transfer between locations respects policies.

---

### FR-04 — Movements (+/–) with Trail and Evidence

**Description**
Record and automate inventory movements with evidence.

**Supported Movements**
- Inbound (internalization)
- Outbound (dispatch/use)
- Transfer
- Reverse (inbound/outbound)
- Reservation / cancellation
- Adjustment (always with HIL)

**Rules**
- Every movement must have:
  - project,
  - type,
  - origin/destination (when applicable),
  - minimum evidence (configurable),
  - author (human/agent) + autonomy level.
- Movement can be "pending" until evidence is complete.

**Acceptance Criteria**
- Movements change balance and states correctly.
- It is possible to audit: "what changed, when, why, and by whom".

---

### FR-05 — Balance by Base/Technician/Project (Operational View)

**Description**
Display consolidated and segmented balance.

**Minimum Views**
- By project (client)
- By location (base/technician)
- By state (available, reserved, in transit, BAD, etc.)
- By criticality (critical items, high value)

**Acceptance Criteria**
- Export view (CSV/PDF) for audit when necessary.
- Quick filters (project, PN, location, state).

---

### FR-06 — Voice / Invoice Reading Input (AI-First)

**Description**
Replace typing with intelligent capture: user "reads" Invoice (or sends PDF) and system fills.

**Rules**
- System must:
  - extract PN, quantities, values, serial (if exists), Invoice and relevant data,
  - suggest project/end client,
  - indicate uncertain fields and request confirmation.
- Must have "learning mode" with user corrections.

**Acceptance Criteria**
- User can complete an inbound without typing main fields.
- Corrections feed memory/training (e.g., supplier X always uses layout Y).

---

### FR-07 — Divergence Detection and Audit (AI)

**Description**
Automatically detect divergence signals and open tasks.

**Divergence Examples**
- Serial appears in two locations at same time.
- Outbound without dispatch evidence.
- Expected reverse did not occur on time.
- Negative balance at any location.
- Abrupt change outside pattern (consumption spikes).

**Acceptance Criteria**
- Divergences generate alert/task with context and recommendation.
- Balance adjustment only occurs with HIL.

---

### FR-08 — Conceptual Integration with Tickets (Tiflux)

**Description**
Each relevant movement needs to be linked to a ticket (parent/child) when exists.

**Rules**
- Module must support:
  - ticket reference (ID) and project,
  - multiple movements per ticket,
  - "child ticket" for logistics when there is no part in bases/advanced stock (via operations process).

**Acceptance Criteria**
- From asset, I can see "which tickets it served".
- From ticket, I can see "which assets were moved".

---

### FR-09 — Permissions, Audit, and Traceability

**Description**
Ensure access control and complete logs.

**Minimum Roles**
- Admin
- Logistics
- Operations
- Technician
- Finance/Tax
- Read (management/audit)

**Acceptance Criteria**
- Sensitive action (adjustment, disposal, restricted transfer) requires role/approval.
- Log shows user/agent, date/time, and changed data.

---

## 12) Module Agents (Observe → Think → Learn → Execute)

> The module is "AI-First": agents are not decoration; they are the flow engine.

### 12.1 Agent — Inventory Control (+/–) (Core)

**Observes**
- ticket events (part request, update, closure)
- dispatch/reverse events (when they exist)
- Invoice / document / confirmation inputs
- inventory counts

**Thinks**
- what movement should occur?
- is there sufficient evidence?
- what is the risk? need HIL?
- is there inconsistency with history?

**Learns**
- when humans correct a suggestion, records:
  - corrected rule,
  - exception by project,
  - supplier pattern.

**Executes**
- creates/reserves/withdraws/transfers according to autonomy level
- creates tasks for logistics/finance when data is missing
- records log and justification

---

### 12.2 Agent — Intake (Invoice/Documents by Voice/PDF)

**Observes**
- uploads, monitored emails, voice recordings, attachments.

**Thinks**
- extract fields, validate consistency (PN x serial x qty),
- estimate confidence by field,
- suggest project and warehouse/status.

**Learns**
- templates by supplier,
- recurring corrections (e.g., "PN comes in field X").

**Executes**
- pre-fills inbound registration,
- signals uncertain fields and opens review.

---

### 12.3 Agent — Reconciliation (SAP/Spreadsheets/Inventory)

**Observes**
- exports, reports, and counts,
- recurring divergences.

**Thinks**
- where is the difference?
- what probable cause (missing movement, serial error, etc.)?

**Learns**
- patterns by project/base,
- divergence seasonality.

**Executes**
- proposes adjustments (always with HIL),
- creates investigation tasks.

---

### 12.4 Agent — Compliance (Policies and Contracts)

**Observes**
- sensitive transfers,
- adjustments, disposals, "missing",
- movements between projects.

**Thinks**
- is it allowed?
- need approval from which role?

**Learns**
- contractual exceptions by project,
- risk profiles.

**Executes**
- blocks, requests approval, and records justification.

---

### 12.5 Agent — Technician Communication (WhatsApp / App)

**Observes**
- pending confirmations and reverse,
- critical events (delays, wrong item, etc.)

**Thinks**
- who to contact?
- what message, with what context?

**Learns**
- response patterns by technician,
- best times/channels.

**Executes**
- sends messages and collects confirmations (with record).

---

## 13) Human-in-the-Loop (HIL) Matrix

| Action | Default Autonomy | Exceptions |
|---|---:|---|
| Create new PN | HIL | Autonomous only if category already exists and low risk |
| Inbound by Invoice with high confidence | Executes with review | HIL if high value or critical serial |
| Reservation by ticket | Autonomous | HIL if transferring between projects |
| Transfer between bases of same project | Autonomous | HIL if "restricted location" or "third-party stock" |
| Inventory adjustment | Mandatory HIL | Never autonomous |
| Disposal / missing | Mandatory HIL | Never autonomous |

---

## 14) User Experience (UI/UX) — Minimum Requirements

### 14.1 Task "Inbox" (Operational)

A single panel where user sees:
- pending inbound (Invoice read, missing confirmation)
- detected divergences
- reservations to stage (pick list)
- overdue reverses
- approval requests (HIL)

### 14.2 Unified Search + Copilot ("Sasha")

- Universal search field + chat mode:
  - "Where is serial X?"
  - "How many PN Y switches exist in RJ and DF?"
  - "Which reverses are pending for more than 5 days?"

Responses must include:
- numbers + locations,
- status,
- "why the system thinks this" (evidence/history).

### 14.3 Mobile/PWA (Minimum Viable)

- Confirm receipt / use / return (technicians).
- Scanner (camera) for serial/QR (if adopted).
- Quick inventory checklist.

---

## 15) Minimum Reports (Within Module)

Even before the complete "Dashboards Module", inventory needs to have:

- Balance by project and by location (with filters).
- Critical items below minimum (when defined).
- Reverse pending (by technician/project).
- Divergences and adjustments (history).
- Timeline by asset (serial).

---

## 16) Legacy Migration and Transition (Product)

### 16.1 Strategy

- Import current spreadsheets as "initial state", but marking **quality/certainty**.
- Run a coexistence period where:
  - system suggests corrections,
  - humans confirm,
  - and confidence grows.
- Gradually replace spreadsheet use with:
  - portal query,
  - task inbox,
  - agent automations.

### 16.2 Migration Requirements (Product)

- Import must accept different spreadsheet "schemas".
- System must map columns to fields, with AI suggestion.
- Must have "missing fields" and "possible duplicates" report.

---

## 17) Risks and Mitigation

- **Risk:** inconsistent historical data → *Mitigation:* mark confidence, do not automate adjustments without HIL, assisted reconciliation.
- **Risk:** agent executes wrong movement → *Mitigation:* autonomy levels, minimum evidence, rollback, and audit.
- **Risk:** contractual rules not coded → *Mitigation:* Compliance Agent + configurable policy by project.
- **Risk:** low technician adoption → *Mitigation:* minimal UX (WhatsApp), contextualized messages, effort reduction.

---

## 18) Dependencies

- Event integration/orchestration (MCP Core) to link tickets ↔ inventory.
- User and permissions catalog (Admin).
- Access to evidence (Invoice, attachments, photos) and retention policies.
- Definition (even if incremental) of:
  - inventory types/locations,
  - required attributes by project,
  - transfer rules between projects,
  - critical items and minimums (when applicable).

---

## 19) MVP Success Criteria (Checklist)

- ✅ Able to record inbound/outbound/transfer with trail and evidence.
- ✅ Able to query balance by base/technician/project in real-time.
- ✅ Able to track a serial from receipt to outbound and return (when exists).
- ✅ Able to operate advanced stock (technician as "location") with simple confirmations.
- ✅ Able to detect basic divergences and create tasks.
- ✅ Able to do inbound by voice/PDF (with HIL) without heavy typing.

---

## Appendix A — Scenario Examples (for Acceptance Testing)

1. **Serialized inbound**: 10 APs arrive with serial; 2 duplicate serials → system blocks and opens exception.
2. **Non-serialized inbound**: 50 cables arrive; balance increases and becomes available.
3. **Reservation by ticket**: operations opens child ticket requesting 1 switch; system reserves and creates pick list.
4. **Transfer to technician**: replenish advanced stock in DF; system transfers and requests technician confirmation on receipt.
5. **Mandatory reverse**: used asset must return; technician does not post in 5 days → system alerts and escalates.
6. **Inventory**: physical count differs; system proposes adjustment and requests approval.



---

## Appendix B — Initial Catalog of "Locations/Inventories" (Example for Parameterization)

> **Objective:** start the module with a *starter pack* of locations that mirrors actual operation.
> **Note:** names below are examples and can/should be normalized (unique ID + nickname).
> **Product:** SGA 2.0 must allow **Project** and **Location** to be related, but not be the same thing (to avoid confusion when a project has multiple bases).

### B.1 Inventories by Project/Client (Examples)
- NTT – Arcos Dourados
- NTT – Necxt
- NTT – IPB
- NTT – KONAMI
- NTT – NTT_ROUTERLINK
- FAISTON
- IMAGINARIUM
- IDM
- ITAÚ
- Linker
- MADERO
- MDS
- ONETRUST
- PORTO SEGURO
- RENNER
- SEM PARAR
- SODEXO
- SUL AMÉRICA
- ZAMP
- SYNGENTA
- Unimed Nacional
- BACKUP

### B.2 Technical Bases (Examples)
- NTT – Montes Claros
- NTT – Rio do Sul
- NTT – Ponta Grossa
- NTT – Ponta Porã
- NTT – Araraquara
- NTT – Itajaí
- NTT – Taubaté
- NTT – Três Lagoas
- NTT – Araçatuba
- NTT – Caruaru
- NTT – Marabá
- NTT – Vitória da Conquista
- NTT – Uruguaiana

### B.3 Self Storage (Examples)
- Self Storage – MG
- Self Storage – SC

### B.4 Service Storage (Examples)
- NTT – Santander SP
- NTT – Santander BV
- NTT – Santander BSB

---

## Appendix C — Data Models (Examples of 10 Assets/Rows)

> **Note:** fictional examples (to align fields and screens). Replace with 5–10 real items as soon as operations sends.

| asset_id | part_number | serial | project | end_client | current_location | location_type | condition | status | ownership |
|---|---|---|---|---|---|---|---|---|---|
| AST-0001 | SW-CISCO-C9200-24T | FOC1234A1B2 | NTT_ROUTERLINK | NTT | Barueri-DC | Logistics Center | New | IN_STOCK | Faiston |
| AST-0002 | AP-ARUBA-515 | CNF9KX1234 | NTT – Arcos Dourados | Arcos Dourados | NTT – Taubaté | Technical Base | Used | IN_USE | Third-party |
| AST-0003 | SSD-1TB-SATA | (n/a) | FAISTON | Internal | Barueri-DC | Logistics Center | New | IN_STOCK | Faiston |
| AST-0004 | NOTE-DELL-5430 | 7H2K9L1 | ITAÚ | Itaú | Technician: João Silva | Technician | Used | IN_USE | Third-party |
| AST-0005 | SWITCH-HP-1920 | HPX1920ZZ9 | NTT – Necxt | Necxt | In transit (Gollog) | In transit | Used | IN_TRANSIT | Third-party |
| AST-0006 | ROUTER-MIKROTIK-RB4011 | MKT4011A77 | ZAMP | Zamp | BAD – Barueri | Logistics Center | BAD | BAD | Third-party |
| AST-0007 | AP-UBIQUITI-U6-LR | U6LR00991 | PORTO SEGURO | Porto | Service Storage – Santander SP | Service Storage | New | IN_STOCK | Faiston |
| AST-0008 | UPS-APC-1500VA | APC15K8890 | MADERO | Madero | Self Storage – MG | Self Storage | Used | IN_STOCK | Third-party |
| AST-0009 | SERVER-DELL-R640 | R640SN0008 | ONETRUST | OneTrust | Barueri-DC (Staging) | Logistics Center | Used | IN_STAGING | Faiston |
| AST-0010 | SWITCH-CISCO-2960X | FCW2960X22 | NTT – IPB | IPB | NTT – Ponta Grossa | Technical Base | Used | AWAITING_REVERSE | Third-party |

---

## Appendix D — Minimum Fields of a Movement (Product Checklist)

**A movement is only "valid" when it has:**
- Movement type (inbound/outbound/transfer/reverse/adjustment/reservation)
- Project (and, when applicable, end client)
- Origin and destination (or "origin = external" on inbound; "destination = external" on outbound)
- PN and/or serial (according to PN rule)
- Quantity (for non-serialized)
- Minimum evidence (attachment, reference, confirmation, etc.)
- Ticket reference (when exists)
- Author and execution mode:
  - human (name/user),
  - or agent (agent name + autonomy A/B/C)
- Timestamp + audit trail
