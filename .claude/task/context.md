# Project Context: Faiston One Platform - Asset Management System

**Last Updated**: 2026-01-09
**Updated By**: system
**Current Phase**: Active Development

---

## Project Overview

### Goal
Build Faiston One Platform as a comprehensive AI-powered Asset Management (Gestao de Ativos) and Inventory Management System featuring:
- **NEXO AI Assistant** - Intelligent copilot for asset operations
- **SGA Module** - Sistema de Gestao de Ativos (Asset Management System)
- Real-time inventory tracking
- Smart Import capabilities (NF-e, spreadsheets)
- Enterprise-grade security and compliance

### Tech Stack
- **Frontend**: React 18 + TypeScript, Vite, TanStack Query, Tailwind CSS, shadcn/ui
- **Backend**: Python 3.11+ with FastAPI, AWS Lambda, AWS Bedrock AgentCore
- **AI Agents**: Google ADK with Gemini 3.0 Pro, AWS Bedrock AgentCore Runtime
- **Database**: DynamoDB (operational), Aurora PostgreSQL (inventory data)
- **Infrastructure**: AWS (Lambda, API Gateway, S3, Cognito, CloudFront), Terraform

### Key Features
- AI-powered NEXO assistant for asset queries and operations
- Smart import of invoices (NF-e) and spreadsheets
- Human-in-the-Loop (HIL) review for low-confidence imports
- Real-time inventory tracking with offline-first PWA support
- Audit logging and compliance tracking
- Role-based access control via AWS Cognito

---

## Architecture Summary

### SGA Module Architecture
Reference: `docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md`

- **Context Provider Hierarchy**: QueryClientProvider -> AssetManagementProvider -> InventoryOperationsProvider
- **Hook Organization**: Data fetching, operation, and import hooks
- **Service Layer**: sgaAgentcore.ts for backend calls
- **Smart Import**: File type detection, agent routing, confidence-based HIL

### Agent Architecture
- **NEXOAgent**: RAG-based AI assistant for asset management
- **FlashcardsAgent**: Study card generation
- **MindMapAgent**: Concept visualization
- **IntakeAgent**: NF-e invoice processing
- **ImportAgent**: Spreadsheet import processing

---

## Key Directories

```
client/                          # React frontend
  app/(main)/ferramentas/ativos/ # SGA module pages
  components/ferramentas/ativos/ # SGA components
  hooks/ativos/                  # SGA hooks
  services/sgaAgentcore.ts       # AgentCore client

server/                          # Backend
  agentcore/                     # AI agents
    agents/                      # Agent implementations
    tools/                       # External integrations
  agentcore-inventory/           # SGA backend
    agents/                      # Inventory agents

terraform/                       # Infrastructure as Code
  main/                          # Main AWS resources
```

---

## Current Focus

### Active Development
- SGA Estoque (Inventory Management) module
- Smart Import features (NF-e, spreadsheets)
- NEXO AI Copilot integration
- Offline-first PWA capabilities

### Next Steps
- Refer to `docs/architecture/SGA_ESTOQUE_ARCHITECTURE.md` for implementation details
- Refer to `docs/prd_modulo_gestao_estoque_faiston_sga2.md` for requirements

---

## Notes

This project uses AI-first architecture with AWS Bedrock AgentCore for all agent operations.
All AI agents run on AgentCore Runtime, not traditional Lambda microservices.
NEXO is the AI assistant that helps users with asset management tasks.

---

**Status**: Active Development
