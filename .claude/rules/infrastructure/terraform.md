---
paths:
  - "terraform/**/*"
  - "**/*.tf"
  - "**/*.tfvars"
---

# Terraform Infrastructure Rules

## Mandatory Practices

1. Use Terraform for **ALL AWS resources**
2. Apply **ALL CORS changes ONLY** in `terraform/main/locals.tf`
3. Run `terraform plan` via GitHub Actions **BEFORE** apply

## Forbidden Practices

1. **NO CloudFormation or SAM** (Terraform ONLY)
2. **NO parallel environments** without consolidation
3. **NO duplicate CORS** (only in `terraform/main/locals.tf`)
4. **NO hardcoded AWS values**
5. **NO local deployments**

## Official Documentation

Use Terraform Registry as source of truth:
- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_gateway
- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime

## Before Any IaC Change

1. Consult AWS AgentCore documentation
2. Consult MCP AWS documentation
3. Consult Terraform Registry docs
4. If unclear → STOP AND ASK
