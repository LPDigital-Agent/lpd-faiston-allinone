# Faiston One - Documentation Hub

> Central documentation index for the Faiston One AI-First Intranet Portal.

---

## Project Overview

**Faiston One** is an AI-First All-in-One Intranet Portal for Faiston employees. The platform is orchestrated by **NEXO**, an AI assistant that handles all interactions, integrations, and automations.

| Aspect | Details |
|--------|---------|
| **Platform** | Faiston One (intranet portal) |
| **AI Assistant** | NEXO (central orchestrator) |
| **Frontend** | Next.js 16 + React 19 + TypeScript + Tailwind CSS 4.0 + shadcn/ui |
| **Backend** | Python 3.13 + Google ADK v1.0 + AWS Lambda (arm64) |
| **AI Runtime** | AWS Bedrock AgentCore (Runtime + Memory + Gateway) |
| **Infrastructure** | Terraform + GitHub Actions CI/CD |
| **Auth** | Amazon Cognito (NO Amplify) |
| **AWS Account** | 377311924364 (us-east-2) |

---

## Documentation Index

### Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [CLAUDE.md](../CLAUDE.md) | Project instructions & AI context | Claude Code / AI Tools |
| [PRD](../product-development/current-feature/PRD.md) | Product Requirements Document | Product / Dev Team |
| [Brand Guide](../docs%20faiston/manual_Faiston_FINAL.pdf) | Visual identity guidelines | Design / Frontend |

### AgentCore Documentation

| Document | Purpose |
|----------|---------|
| [IMPLEMENTATION_GUIDE.md](AgentCore/IMPLEMENTATION_GUIDE.md) | Complete AgentCore architecture and implementation rules |
| [Identity_Implementation_guide.md](AgentCore/Identity_%20Implementation_guide.md) | AgentCore Identity v1.0 compliance guide |
| [agentcore-adk-framework.md](AgentCore/agentcore-adk-framework.md) | Google ADK framework integration |
| [agentcore-gateway.md](AgentCore/agentcore-gateway.md) | MCP Gateway configuration |
| [agentcore-invokeAgent.md](AgentCore/agentcore-invokeAgent.md) | Agent invocation patterns |
| [agentcore-stream-websock.md](AgentCore/agentcore-stream-websock.md) | Streaming and WebSocket protocols |

### Agent Documentation

| Document | Purpose |
|----------|---------|
| [ADK_AGENTCORE_ARCHITECT.md](agents/ADK_AGENTCORE_ARCHITECT.md) | Agent architecture specialist guide |

### Architecture Documentation

| Document | Purpose |
|----------|---------|
| [SGA_ESTOQUE_ARCHITECTURE.md](architecture/SGA_ESTOQUE_ARCHITECTURE.md) | SGA Inventory module architecture |
| [INFRASTRUCTURE.md](INFRASTRUCTURE.md) | AWS infrastructure documentation |

### Operations Documentation

| Document | Purpose |
|----------|---------|
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and solutions |
| [CI_CD_WORKFLOWS.md](CI_CD_WORKFLOWS.md) | GitHub Actions deployment workflows |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Aurora PostgreSQL and DynamoDB schemas |
| [AGENT_CATALOG.md](AGENT_CATALOG.md) | Complete inventory of all 22 AI agents |
| [SGA_EQUIPMENT_KB_SETUP.md](SGA_EQUIPMENT_KB_SETUP.md) | Equipment Knowledge Base setup |

### Claude Code Best Practices

| Document | Purpose |
|----------|---------|
| [claude-code-best-practices.md](Claude%20Code/claude-code-best-practices.md) | General Claude Code usage guidelines |
| [claude-code-prompting-best-practices.md](Claude%20Code/claude-code-prompting-best-practices.md) | Prompt engineering for Claude Code |

### Feature Documentation

| Document | Purpose |
|----------|---------|
| [Faiston_Investory_Mamagement.md](Faiston_Investory_Mamagement.md) | SGA Inventory management overview |
| [prd_modulo_gestao_estoque_faiston_sga2.md](prd_modulo_gestao_estoque_faiston_sga2.md) | SGA 2.0 detailed PRD |
| [Modulo_Gestao_Estoque_ModuloExpedicao.pdf](Modulo_Gestao_Estoque_ModuloExpedicao.pdf) | Expedition module specification |
| [Agent Room Plan](../.claude/plans/golden-bouncing-hearth.md) | Agent Room transparency window design |

### Authentication Documentation

| Document | Purpose |
|----------|---------|
| [FRONTEND_AUTH.md](FRONTEND_AUTH.md) | Frontend authentication architecture |
| [FRONTEND_AUTH_IMPLEMENTATION.md](FRONTEND_AUTH_IMPLEMENTATION.md) | Auth implementation details |

---

## Quick Start

### Prerequisites

- Node.js 20+ with pnpm
- Python 3.13+
- AWS CLI configured
- Terraform 1.5+

### Development Setup

```bash
# Clone repository
git clone https://github.com/lpd-faiston-allinone.git
cd lpd-faiston-allinone

# Frontend
cd client
pnpm install
pnpm dev          # http://localhost:3000

# Backend (AgentCore agents)
cd server/agentcore-academy
pip install -r requirements.txt
```

### Key Commands

| Command | Purpose |
|---------|---------|
| `pnpm dev` | Start frontend dev server |
| `pnpm build` | Production build |
| `pnpm typecheck` | TypeScript validation |
| `terraform plan` | Preview infrastructure changes |
| `agentcore status` | Check AgentCore deployment |

---

## Project Structure

```
lpd-faiston-allinone/
├── .claude/                 # Claude Code configuration
│   ├── commands/           # Slash commands (/commit, /prime, etc.)
│   └── skills/             # Specialist skills
├── client/                 # Next.js 15 frontend
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   ├── hooks/             # Custom hooks
│   ├── lib/               # Utilities
│   └── services/          # API clients (AgentCore)
├── server/                 # Python backend
│   ├── agentcore-inventory/ # SGA agents (30+ actions, 14 agents, 18 tools)
│   └── agentcore-portal/  # Portal NEXO agents (includes Academy features)
├── terraform/             # AWS Infrastructure as Code
│   └── main/              # All AWS resources
├── docs/                  # Documentation (this folder)
└── docs faiston/          # Brand assets
```

---

## Modules

### Faiston Academy

Educational platform with AI-powered learning features:
- NEXO AI Tutor (chat)
- Flashcards generation
- Mind Map visualization
- Audio Class (ElevenLabs TTS)
- Video Class generation
- Slide Deck creation
- HeyGen personalized videos

**Location**: `/ferramentas/academy/`

### SGA Inventory (Gestao de Estoque)

Asset/inventory management system with **100% A2A Agentic Architecture**:
- **NEXO Intelligent Import**: TRUE agentic import with ReAct pattern (OBSERVE → THINK → ASK → LEARN → ACT)
- **Schema-Aware Import**: Dynamic column matching via PostgreSQL introspection
- Multi-source entry (NF, OCR, SAP, Manual)
- Smart Import (auto-detect XML/PDF/CSV/XLSX/JPG/PNG/TXT)
- Expedition with AI guidance
- Reverse logistics
- SAP reconciliation
- Analytics dashboard
- **Agent Room**: Transparency window for AI visibility (see below)

**Architecture (A2A Protocol)**:
- **14 AgentCore Runtimes** (one per agent, JSON-RPC 2.0 over HTTP)
- **Communication**: A2A Protocol (port 9000) - no Python imports between agents
- **Memory**: AgentCore Memory (global namespace `/strategy/import/company`)
- **Warm-Up**: EventBridge pings critical agents every 10 minutes to prevent cold starts
- **Key Agents**: nexo_import (orchestrator), learning, validation, intake, estoque_control

**Backend**: 14 dedicated runtimes, 20 tools (PostgreSQL, schema validation, S3, HIL)
**Frontend**: 6 contexts, 29 hooks, 25+ pages

**Location**: `/ferramentas/ativos/estoque/`

### Agent Room (Sala de Transparência)

AI transparency dashboard for non-technical users to see what agents do "behind the scenes":
- **Live Feed**: Real-time humanized messages in Portuguese (first-person)
- **Agent Team**: Visual cards showing all 14 AI agents with friendly names and status
- **Learning Stories**: What agents have learned from interactions
- **Workflow Timeline**: Visual progress of current operations
- **Pending Decisions**: HIL tasks requiring human input

**Design**: Apple TV frosted dark glass (NEXO Copilot pattern)
**Architecture**: TanStack Query polling (5s) with backend aggregation
**Backend Action**: `get_agent_room_data` (single endpoint returns all data)
**Event System**: `emit_agent_event()` writes AGENT_ACTIVITY events to DynamoDB audit log

**Key Files**:
- Backend: `server/agentcore-inventory/tools/agent_room_service.py` (emit, aggregate)
- Backend: `server/agentcore-inventory/tools/humanizer.py` (Portuguese messages)
- Frontend: `client/hooks/ativos/useAgentRoomStream.ts` (polling hook)
- Frontend: `client/components/ferramentas/ativos/agent-room/` (UI components)

**Location**: `/ferramentas/ativos/agent-room/`

---

## Security & Compliance

This platform follows security-first development practices:

### Security References

| Standard | Purpose |
|----------|---------|
| [OWASP](https://owasp.org/) | Web application security |
| [NIST CSF](https://www.nist.gov/cyberframework) | Cybersecurity framework |
| [MITRE ATT&CK](https://attack.mitre.org/) | Threat intelligence |
| [CWE](https://cwe.mitre.org/) | Weakness enumeration |
| [SANS](https://www.sans.org/) | Security training |
| [CIS](https://www.cisecurity.org/) | Security benchmarks |
| [AWS Security](https://aws.amazon.com/security/) | Cloud security |
| [AWS Well-Architected](https://aws.amazon.com/architecture/well-architected/security/) | Security pillar |
| [Microsoft SDL](https://www.microsoft.com/security/sdl) | Secure development lifecycle |

### Security Practices

- JWT Bearer token authentication (Cognito)
- **AgentCore Identity v1.0 compliance** (all 14 agents use `identity_utils.py`)
- User identity extracted from `context.identity` (JWT validated), not payload
- No hardcoded credentials (GitHub Secrets)
- Terraform-only infrastructure (no manual AWS changes)
- CI/CD deployment only (no local console deploys)
- Input validation at all boundaries
- CORS configured centrally in Terraform

---

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `terraform.yml` | Push to `terraform/**` | Infrastructure deployment |
| `deploy-frontend.yml` | Push to `client/**` | Frontend to S3/CloudFront |
| `deploy-agentcore-inventory.yml` | Push/Manual | SGA agents |
| `deploy-agentcore-portal.yml` | Push/Manual | Portal NEXO agents (includes Academy) |
| `deploy-sga-postgres-lambda.yml` | Push/Manual | PostgreSQL MCP tools Lambda (11 tools) |
| `migrate-sga-schema.yml` | Manual | Apply PostgreSQL schema via Lambda bridge |
| `update-sga-gateway-target.yml` | Manual | Update MCP Gateway Target tool definitions |

---

## Contributing

### Documentation Guidelines

1. **Location**: All documentation in `docs/` folder
2. **Format**: Markdown with proper headings
3. **Code Examples**: Test before committing
4. **Links**: Use relative paths
5. **Language**: ALL documentation in English (standardized)

### Adding New Documentation

1. Create file in appropriate `docs/` subdirectory
2. Add entry to this README.md index
3. Run `/commit` to save changes

---

## Claude Code Commands

| Command | Purpose |
|---------|---------|
| `/prime` | Load project context after `/clear` |
| `/sync-project` | Sync documentation and memory |
| `/commit` | Create well-formatted git commit |
| `/ship` | Commit and push to GitHub |
| `/branch` | Create feature branch with `fabio/` prefix |
| `/check` | Run lint, build, and tests |

---

## Support

- **Claude Code**: Use `/prime` to load project context
- **Skills**: Use available skills for specialized tasks

---

*Last updated: January 2026*
*Platform: Faiston NEXO*
