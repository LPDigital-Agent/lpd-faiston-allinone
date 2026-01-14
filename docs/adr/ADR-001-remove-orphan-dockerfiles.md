# ADR-001: Remove Orphan Dockerfiles from AgentCore Agents

## Status

**Accepted** (2026-01-14)

## Context

During a codebase audit, we discovered **14 Dockerfiles** in the `server/agentcore-inventory/agents/*/` directories. These files defined container images for each agent but were **never used in production**.

### Evidence of Non-Usage

1. **`.bedrock_agentcore.yaml`** explicitly sets:
   ```yaml
   deployment_type: direct_code_deploy
   container_runtime: null
   ecr_repository: null
   ```

2. **Terraform configuration** (`agentcore_runtimes.tf`) uses ZIP-based deployment:
   ```hcl
   code {
     s3 {
       bucket = "faiston-one-sga-documents-prod"
       prefix = "agentcore/agents/${agent}/agent.zip"
     }
   }
   ```

3. **GitHub Actions workflow** packages agents as ZIP files, not Docker images.

### Problem

The presence of Dockerfiles contradicted the actual deployment strategy, causing:
- Potential confusion for developers
- Maintenance overhead for unused code
- Violation of "REAL STATE OVER DOCUMENTATION" principle (CLAUDE.md)

## Decision

**Remove all 14 Dockerfiles** from the agent directories.

### Affected Files

```
server/agentcore-inventory/agents/
├── carrier/Dockerfile          ← REMOVED
├── compliance/Dockerfile       ← REMOVED
├── data_import/Dockerfile      ← REMOVED
├── equipment_research/Dockerfile ← REMOVED
├── estoque_control/Dockerfile  ← REMOVED
├── expedition/Dockerfile       ← REMOVED
├── intake/Dockerfile           ← REMOVED
├── learning/Dockerfile         ← REMOVED
├── nexo_import/Dockerfile      ← REMOVED
├── observation/Dockerfile      ← REMOVED
├── reconciliacao/Dockerfile    ← REMOVED
├── reverse/Dockerfile          ← REMOVED
├── schema_evolution/Dockerfile ← REMOVED
└── validation/Dockerfile       ← REMOVED
```

## Consequences

### Positive

- **Cleaner codebase**: ~584 lines of dead code removed
- **No confusion**: Deploy strategy is now unambiguous (ZIP-based)
- **Aligned with CLAUDE.md**: "REAL STATE OVER DOCUMENTATION"

### Negative

- **Lost reference**: Dockerfiles could have served as local development reference
- **Mitigation**: If needed, developers can reconstruct from `requirements.txt` and `main.py`

## Alternatives Considered

1. **Move to `docs/docker-reference/`**: Preserves as documentation but still maintains confusion
2. **Add README explaining purpose**: Zero removal but still has code that doesn't run in prod

Both alternatives were rejected in favor of clean removal.

## Related

- **CLAUDE.md**: "REAL STATE OVER DOCUMENTATION (MANDATORY)"
- **Deploy workflow**: `.github/workflows/deploy-agentcore-sga-agents.yml`
- **Terraform**: `terraform/main/agentcore_runtimes.tf`

## Notes

AWS Bedrock AgentCore Runtime supports both ZIP and container-based deployments. This project chose ZIP-based (`direct_code_deploy`) for simplicity and faster iteration cycles.
