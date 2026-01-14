---
paths:
  - "terraform/**/*"
  - "**/*.tf"
  - "**/*.tfvars"
  - ".github/workflows/**/*"
  - "scripts/**/*"
  - "server/**/*"
---

# AWS Configuration Rules

## Account & Region

- **AWS Account ID:** `377311924364`
- **AWS Region:** `us-east-2`
- **AWS CLI Profile:** `faiston-aio`

## CLI Profile Policy

- For ANY AWS CLI command, MUST use profile `--profile faiston-aio`
- Never run AWS CLI without explicitly setting the profile
- If profile unavailable/not configured → STOP and ask

## AgentCore CLI

For AgentCore configurations and CLI changes:
- https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html

## Authentication Policy

- **NO AWS AMPLIFY — EVER**
- **Amazon Cognito** is the PRIMARY authentication method
- Direct API usage only
- NO SDK abstractions

## MCP Access Policy

- ALL MCP tools/servers MUST be accessed via **AWS Bedrock AgentCore Gateway**
- Use AgentCore Gateway MCP endpoint for tool discovery/invocation (`tools/list`, `tools/call`)
- Do NOT call tool endpoints directly

## Inventory Datastore

- Inventory data MUST live in **AWS Aurora PostgreSQL (RDS)**
- **DO NOT USE DynamoDB**
- Any assumption otherwise is WRONG
