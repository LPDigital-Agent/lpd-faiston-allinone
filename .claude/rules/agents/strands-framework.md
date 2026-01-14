---
paths:
  - "**/*agent*.py"
  - "**/*agent*.ts"
  - ".claude/agents/**/*"
  - "server/agents/**/*"
  - "server/**/agent*.py"
---

# AWS Strands Agents Framework Rules

> ALL agents MUST be created using the AWS STRANDS AGENTS FRAMEWORK.

## Official Documentation (Source of Truth)

- https://strandsagents.com/latest/
- https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
- https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-frameworks/strands-agents.html
- https://github.com/strands-agents/sdk-python
- https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/
- https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/
- https://aws.amazon.com/blogs/opensource/introducing-strands-agent-sops-natural-language-workflows-for-ai-agents/

## A2A / Inter-Agent Communication

- https://builder.aws.com/content/2y90GhUwgOEbKULKuehf2WHUf9Q/leveraging-agent-to-agent-a2a-with-strands-part-1
- https://aws.amazon.com/blogs/opensource/open-protocols-for-agent-interoperability-part-4-inter-agent-communication-on-a2a/

## LLM Policy (Gemini 2.5 Family)

- **ALL agents MUST use GEMINI 2.5 FAMILY**
- **Critical Inventory Agents:** Use GEMINI 2.5 PRO with THINKING ENABLED for:
  - Stock/inventory file analysis (XML/PDF/CSV/XLSX/images)
  - Reasoning over extracted data
  - HIL clarification questions
  - Mapping validation and reconciliation
- **Non-Critical Agents:** MAY use GEMINI 2.5 FLASH

### Temporary Exception (Strands SDK Limitation)

- Strands SDK does NOT YET support Gemini 2.5 natively
- Agents using Strands A2A on AWS Bedrock AgentCore MAY use Gemini 2.5 Pro as workaround
- Monitor https://strandsagents.com/latest/ for Gemini 2.5 support
- When support arrives → migrate ALL agents and REMOVE this exception

## Gemini Documentation

- https://ai.google.dev/gemini-api/docs/gemini-3
- https://ai.google.dev/gemini-api/docs/thinking
- https://ai.google.dev/gemini-api/docs/files

## AgentCore Memory Model

Agents run on AWS Bedrock AgentCore with its MANAGED MEMORY SYSTEM.

**MANDATORY Memory Types:**
- Session Memory
- Short-Term Memory (STM)
- Long-Term Memory (LTM)
- RAG where applicable

**FORBIDDEN:**
- Treating agents as stateless Lambdas
- Implementing custom memory outside AgentCore without approval
- Bypassing AgentCore memory mechanisms

**Memory Documentation:**
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-types.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-strategies.html
