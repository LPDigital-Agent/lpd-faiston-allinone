# ADK AgentCore Architect Agent

Claude Code custom agent specialized in designing, building, and deploying AI agents using Google ADK, A2A protocols, and AWS Bedrock AgentCore.

---

## Table of Contents

1. [Overview](#overview)
2. [When to Use This Agent](#when-to-use-this-agent)
3. [Core Expertise](#core-expertise)
4. [Capabilities](#capabilities)
5. [Methodology](#methodology)
6. [Hive Academy Project Rules](#hive-academy-project-rules)
7. [Usage Example](#usage-example)
8. [Related Documentation](#related-documentation)

---

## Overview

The `adk-agentcore-architect` agent is an elite AI Agent Architect with deep expertise in three key technologies:

| Technology | Purpose |
|------------|---------|
| **Google ADK** | Framework for building AI agents (SashaAgent, FlashcardsAgent, etc.) |
| **A2A Protocol** | Agent-to-Agent communication patterns |
| **AWS Bedrock AgentCore** | AWS runtime environment where agents execute |

The Hive Academy project uses a sophisticated architecture that combines these technologies:

```
Frontend (React SPA)
    |
    v
Cognito JWT Authentication
    |
    v
AWS Bedrock AgentCore Runtime
    |
    v
Google ADK Agents (Python)
    |
    v
LLM Providers (Bedrock/Gemini)
```

This agent understands the entire stack and can provide guidance on any layer.

---

## When to Use This Agent

| Scenario | Example |
|----------|---------|
| Create new agent | "I need to create an agent to help students with math problems" |
| A2A communication | "How do I make SashaAgent call FlashcardsAgent?" |
| Debug deployment | "My agent doesn't respond after deploying to AgentCore" |
| Add RAG capabilities | "I want to add document search to ReflectionAgent" |
| Switch LLM model | "How do I change from Gemini to Claude on Bedrock?" |
| Optimize performance | "My agent is too slow, how can I improve latency?" |
| Implement tools | "I need to add ElevenLabs TTS to my agent" |
| Session management | "How do I persist conversation history between requests?" |

---

## Core Expertise

The agent possesses specialized knowledge in the following areas:

### Why This Specialization Exists

Hive Academy uses a complex AI agent architecture that requires knowledge across multiple domains:

1. **Google ADK** for agent structure and behavior
2. **AWS Bedrock AgentCore** for runtime execution on AWS
3. **LiteLLM** for model provider abstraction
4. **ElevenLabs** for text-to-speech integration

The agent knows how to navigate this stack and consults updated documentation via MCP tools before responding.

### Existing Agents in Hive Academy

| Agent | Purpose | File |
|-------|---------|------|
| SashaAgent | RAG-based tutoring chat | `server/agentcore/agents/sasha_agent.py` |
| FlashcardsAgent | Study card generation | `server/agentcore/agents/flashcards_agent.py` |
| MindMapAgent | Concept visualization | `server/agentcore/agents/mindmap_agent.py` |
| ReflectionAgent | Learning analysis | `server/agentcore/agents/reflection_agent.py` |
| AudioClassAgent | Audio lessons + TTS | `server/agentcore/agents/audioclass_agent.py` |

---

## Capabilities

### Google ADK

| Capability | Description |
|------------|-------------|
| Agent Design Patterns | All ADK agent types, lifecycle hooks, state management |
| Tool Creation | Custom tools, function declarations, tool orchestration |
| Memory Systems | Short-term, long-term, and session-based memory |
| RAG Integration | Retrieval-augmented generation patterns with ADK |
| Multi-Modal Agents | Text, audio, image, and video processing agents |
| Streaming & Events | Streaming responses and event-driven architectures |

### A2A Protocol

| Capability | Description |
|------------|-------------|
| Agent Communication | Inter-agent messaging, delegation, collaboration patterns |
| Agent Discovery | Registration, capability advertisement, routing |
| Handoff Patterns | Seamless task handoffs between specialized agents |
| Error Propagation | Graceful failure handling across agent boundaries |
| State Synchronization | Shared state and context management between agents |

### AWS Bedrock AgentCore

| Capability | Description |
|------------|-------------|
| Runtime Configuration | AgentCore setup, scaling, optimization |
| Model Integration | Bedrock models (Claude, Titan) and external (Gemini) |
| Action Groups | Agent capability design and implementation |
| Knowledge Bases | RAG configuration and optimization |
| Guardrails | Content filtering, PII protection, safety |
| Session Management | Multi-turn conversations, session persistence |
| Observability | Logging, tracing, monitoring setup |
| IAM & Security | Least-privilege access, secure deployments |

---

## Methodology

The agent follows a structured process when providing solutions:

### When Designing Agents

1. **Gather Requirements** - Clarify the agent's purpose, capabilities, and constraints
2. **Research Documentation** - Fetch latest docs via MCP tools (AWS, Context7)
3. **Architecture Design** - Create clear architecture diagram and component breakdown
4. **Implementation Plan** - Provide complete, production-ready code
5. **Testing Strategy** - Define how to test agent behavior and edge cases
6. **Deployment Guide** - Specify deployment via GitHub Actions (never local!)

### When Troubleshooting

1. **Diagnose** - Identify the layer where the issue occurs (ADK, AgentCore, model, network)
2. **Research** - Check documentation for known issues and solutions
3. **Isolate** - Create minimal reproduction cases
4. **Fix** - Provide targeted solutions with explanations
5. **Prevent** - Suggest monitoring and alerting for future issues

### Documentation Research (Mandatory)

The agent always:
- Uses AWS MCP to fetch current Bedrock AgentCore documentation
- Uses Context7 MCP to fetch current Google ADK documentation
- Cross-references multiple sources when approaches differ
- Never relies solely on training data (documentation changes frequently)

---

## Hive Academy Project Rules

The agent is pre-configured with Hive Academy policies:

### Infrastructure Rules

| Rule | Description |
|------|-------------|
| Terraform Only | Never use CloudFormation/SAM - all AWS resources via Terraform |
| GitHub Actions | Deploy only via CI/CD - never from local console |
| No Hardcoded Values | Use Terraform variables/locals for AWS configuration |
| Check Before Create | Always verify existing resources before creating new ones |

### Authentication

| Setting | Value |
|---------|-------|
| App Auth | Simple mock authentication (FastAPI backend) |
| AgentCore Auth | Cognito JWT tokens |
| Demo Credentials | `demo@hive.academy` / `Password123` |
| Amplify | NEVER use AWS Amplify |

### Deployment Workflow

Agents are deployed via: `.github/workflows/deploy-agentcore.yml`

**Triggers:**
- Push to `server/agentcore/**`
- Manual workflow dispatch

### Security Standards

- Never hardcode credentials or API keys
- Use SSM Parameter Store or Secrets Manager for secrets
- Implement proper IAM roles with least privilege
- Validate and sanitize all inputs to agents
- Enable CloudWatch logging for audit trails

---

## Usage Example

### Scenario: Creating a Quiz Agent

**User Request:**
```
"I want to create a new agent to generate quizzes that test student knowledge"
```

**Agent Response Process:**

1. **Research Documentation**
   - Fetch latest Google ADK documentation via MCP
   - Review `docs/AgentCore/IMPLEMENTATION_GUIDE.md`

2. **Design Architecture**
   - Define QuizAgent extending `GoogleADKAgentBase`
   - Plan input/output schema
   - Design prompts for quiz generation

3. **Generate Implementation**
   ```python
   # server/agentcore/agents/quiz_agent.py
   from .base import GoogleADKAgentBase

   class QuizAgent(GoogleADKAgentBase):
       """Generates quizzes from lesson content."""

       def __init__(self):
           super().__init__(
               name="QuizAgent",
               model="gemini/gemini-2.5-flash"
           )

       async def generate_quiz(
           self,
           transcription: str,
           num_questions: int = 5,
           difficulty: str = "medium"
       ) -> dict:
           # Implementation...
   ```

4. **Update Entrypoint**
   - Add routing in `server/agentcore/main.py`
   - Register new action handler

5. **Create Frontend Hook**
   - Generate `client/hooks/useQuiz.ts`
   - Integrate with AgentCore client

6. **Terraform Resources**
   - No new AWS resources needed (uses existing AgentCore runtime)
   - Or specify required resources if needed

7. **Deployment Steps**
   - Push changes to `server/agentcore/`
   - GitHub Actions automatically triggers deployment
   - Verify via CloudWatch logs

---

## Related Documentation

### Hive Academy Docs

| Document | Purpose |
|----------|---------|
| [AgentCore/IMPLEMENTATION_GUIDE.md](../AgentCore/IMPLEMENTATION_GUIDE.md) | Complete AgentCore implementation reference |
| [INFRASTRUCTURE.md](../INFRASTRUCTURE.md) | AWS infrastructure and Terraform configuration |
| [FLASHCARDS_BACKEND.md](../FLASHCARDS_BACKEND.md) | Example agent implementation |
| [AUDIOCLASS_FEATURE.md](../AUDIOCLASS_FEATURE.md) | Agent with TTS integration |
| [MINDMAP_FEATURE.md](../MINDMAP_FEATURE.md) | Agent with structured output |

### Key Source Files

| File | Purpose |
|------|---------|
| `server/agentcore/main.py` | BedrockAgentCoreApp entrypoint |
| `server/agentcore/agents/base.py` | GoogleADKAgentBase with LiteLLM |
| `client/services/agentcore.ts` | Frontend AgentCore client |
| `client/services/cognito.ts` | Cognito JWT token acquisition |
| `.github/workflows/deploy-agentcore.yml` | Deployment workflow |

### External Documentation

- [Google ADK Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/agent-builder)
- [AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [A2A Protocol Specification](https://google.github.io/A2A/)

---

## Agent Configuration

**Location:** `.claude/agents/adk-agentcore-architect.md`

**Model:** Sonnet (claude-3.5-sonnet)

**Color:** Orange

**Invocation:** Automatic when Claude detects agent-related tasks, or explicitly via:
```
Use the adk-agentcore-architect agent to help with this task
```

---

**Last Updated:** December 2025
