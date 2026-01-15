# CONTEXT SNAPSHOT (AUTO)
Updated: 2026-01-15 00:15:00 UTC

## Current Goal
- BUG-017 v2 FIX: NEXO Smart Import upload URL failure - DEPLOYED, PENDING VERIFICATION
- /sync-project: Synchronize documentation and MCP memory - COMPLETED

## Current Plan (Next 3 Steps)
1. ✅ BUG-017 v2 fix deployed via GitHub Actions
2. Verify upload URL flow works in production
3. Test full NEXO Smart Import flow end-to-end

## Last Turn Summary
- User: `/sync-project` command
- Assistant: Executed sync-project phases 1-8, updated prime.md with ADR-002 structure, updated README.md, synchronized MCP memory with BUG-017 and ADR-002 entities

## Active Constraints (from CLAUDE.md)
- AI-FIRST / AGENTIC architecture only (no traditional microservices)
- AWS Bedrock AgentCore for all agents (Strands Agents Framework)
- Terraform only (no CloudFormation/SAM)
- Amazon Cognito for auth (no Amplify)
- Aurora PostgreSQL for inventory (no DynamoDB)
- Python 3.13 + arm64 for all Lambdas
- Gemini 2.5 family for all agent LLMs

## Recent Changes (2026-01-14 → 2026-01-15)
- **BUG-017 v2 FIX:** Direct S3 tool call bypassing A2A (Mode 2.5)
- **ADR-002:** "Everything is an Agent" architecture with orchestrators/specialists
- **prime.md:** Updated with ADR-002 structure and routing modes
- **README.md:** Updated with ADR-002 architecture and ADR docs section

## Active ADRs
- **ADR-001:** Remove orphan Dockerfiles (ZIP deploy only) ✅ IMPLEMENTED
- **ADR-002:** Faiston Agent Ecosystem ("Everything is an Agent") ✅ IMPLEMENTED

## Risks / Blockers
- BUG-017: Awaiting production verification after GitHub Actions deployment
- Cold start: Critical agents have 10-minute EventBridge warm-up pings

