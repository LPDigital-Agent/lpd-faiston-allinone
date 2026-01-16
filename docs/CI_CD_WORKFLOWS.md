# CI/CD Workflows Guide - Faiston NEXO

GitHub Actions workflows for automated deployment of the Faiston NEXO platform.

## Table of Contents

1. [Overview](#1-overview)
2. [Workflow Architecture](#2-workflow-architecture)
3. [Frontend Deployment](#3-frontend-deployment)
4. [AgentCore Deployment](#4-agentcore-deployment)
5. [Terraform Workflows](#5-terraform-workflows)
6. [Secrets Configuration](#6-secrets-configuration)
7. [Branch Protection](#7-branch-protection)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Overview

### Deployment Philosophy

| Principle | Implementation |
|-----------|----------------|
| **No Local Deploys** | All deployments via GitHub Actions |
| **Terraform Only** | NO CloudFormation, NO SAM |
| **Branch Protection** | PR required for main branch |
| **Secrets Management** | GitHub Secrets for credentials |

### Workflow Files

| Workflow | File | Triggers |
|----------|------|----------|
| Frontend Deploy | `.github/workflows/deploy-frontend.yml` | Push to `client/**` |
| AgentCore Inventory | `.github/workflows/deploy-agentcore-inventory.yml` | Push to `server/agentcore-inventory/**` |
| AgentCore Academy | `.github/workflows/deploy-agentcore-academy.yml` | Push to `server/agentcore-academy/**` |
| AgentCore Portal | `.github/workflows/deploy-agentcore-portal.yml` | Push to `server/agentcore-portal/**` |
| Terraform Plan | `.github/workflows/terraform-plan.yml` | PR to main |
| Terraform Apply | `.github/workflows/terraform-apply.yml` | Merge to main |

---

## 2. Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       GitHub Actions                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PR Created                 Merge to Main                       │
│      │                           │                              │
│      ▼                           ▼                              │
│  ┌──────────┐              ┌──────────┐                        │
│  │ Lint     │              │ Build    │                        │
│  │ Test     │              │ Deploy   │                        │
│  │ Plan     │              │ Notify   │                        │
│  └──────────┘              └──────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Account                             │
│                        377311924364                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │CloudFront│  │AgentCore │  │AgentCore │  │ Aurora   │       │
│  │  + S3    │  │ Inventory│  │ Academy  │  │PostgreSQL│       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Frontend Deployment

### Workflow File

```yaml
# .github/workflows/deploy-frontend.yml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'client/**'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: client/package-lock.json

      - name: Install Dependencies
        working-directory: client
        run: npm ci

      - name: Build
        working-directory: client
        run: npm run build
        env:
          NEXT_PUBLIC_COGNITO_USER_POOL_ID: ${{ secrets.COGNITO_USER_POOL_ID }}
          NEXT_PUBLIC_COGNITO_CLIENT_ID: ${{ secrets.COGNITO_CLIENT_ID }}
          NEXT_PUBLIC_AWS_REGION: us-east-2

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-2

      - name: Deploy to S3
        working-directory: client
        run: |
          aws s3 sync out/ s3://faiston-one-frontend-prod \
            --delete \
            --cache-control "public, max-age=31536000, immutable" \
            --exclude "*.html" \
            --exclude "_next/data/*"

          aws s3 sync out/ s3://faiston-one-frontend-prod \
            --delete \
            --cache-control "public, max-age=0, must-revalidate" \
            --include "*.html" \
            --include "_next/data/*"

      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

### Build Configuration

The frontend uses Next.js 16 with static export:

```javascript
// client/next.config.js
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};
```

---

## 4. AgentCore Deployment

### Inventory Runtime

```yaml
# .github/workflows/deploy-agentcore-inventory.yml
name: Deploy AgentCore Inventory

on:
  push:
    branches: [main]
    paths:
      - 'server/agentcore-inventory/**'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-2

      - name: Install AgentCore CLI
        run: pip install bedrock-agentcore-starter-toolkit --quiet

      - name: Deploy to AgentCore
        working-directory: server/agentcore-inventory
        run: |
          agentcore deploy \
            --agent faiston_inventory_orchestration \
            --env GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }} \
            --env AWS_REGION=us-east-2 \
            --env COGNITO_USER_POOL_ID=${{ secrets.COGNITO_USER_POOL_ID }} \
            --env COGNITO_CLIENT_ID=${{ secrets.COGNITO_CLIENT_ID }}
```

### Academy Runtime

```yaml
# .github/workflows/deploy-agentcore-academy.yml
name: Deploy AgentCore Academy

on:
  push:
    branches: [main]
    paths:
      - 'server/agentcore-academy/**'
  workflow_dispatch:

# Platform: Faiston One

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-2

      - name: Install AgentCore CLI
        run: pip install bedrock-agentcore-starter-toolkit --quiet

      - name: Deploy to AgentCore
        working-directory: server/agentcore-academy
        run: |
          agentcore deploy \
            --agent faiston_academy_agents \
            --env GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }} \
            --env ELEVENLABS_API_KEY=${{ secrets.ELEVENLABS_API_KEY }}
```

---

## 5. Terraform Workflows

### Plan on PR

```yaml
# .github/workflows/terraform-plan.yml
name: Terraform Plan

on:
  pull_request:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-2

      - name: Terraform Init
        working-directory: terraform/main
        run: terraform init

      - name: Terraform Plan
        working-directory: terraform/main
        run: terraform plan -no-color -out=tfplan
        continue-on-error: true

      - name: Comment Plan on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('terraform/main/tfplan', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan\n\`\`\`hcl\n${plan}\n\`\`\``
            });
```

### Apply on Merge

```yaml
# .github/workflows/terraform-apply.yml
name: Terraform Apply

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  apply:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-2

      - name: Terraform Init
        working-directory: terraform/main
        run: terraform init

      - name: Terraform Apply
        working-directory: terraform/main
        run: terraform apply -auto-approve
```

---

## 6. Secrets Configuration

### Required Secrets

| Secret | Description | Where to Get |
|--------|-------------|--------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key | AWS IAM Console |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key | AWS IAM Console |
| `COGNITO_USER_POOL_ID` | Cognito pool ID | `us-east-2_lkBXr4kjy` |
| `COGNITO_CLIENT_ID` | Cognito client ID | `7ovjm09dr94e52mpejvbu9v1cg` |
| `GOOGLE_API_KEY` | Google Gemini API key | Google Cloud Console |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS API key | ElevenLabs Dashboard |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront dist ID | AWS CloudFront Console |

### Adding Secrets

1. Navigate to **Repository Settings** > **Secrets and variables** > **Actions**
2. Click **New repository secret**
3. Add each secret with its value

### Environment Variables

For environment-specific secrets, use GitHub Environments:

1. Create a `production` environment in Repository Settings
2. Add environment-specific secrets there
3. Reference with `environment: production` in workflow

---

## 7. Branch Protection

### Main Branch Rules

Configure these rules in **Settings** > **Branches** > **Branch protection rules**:

| Rule | Setting |
|------|---------|
| **Require PR before merge** | Enabled |
| **Require approvals** | 1 approval minimum |
| **Require status checks** | `lint`, `test`, `terraform-plan` |
| **Require branches to be up to date** | Enabled |
| **Restrict pushes** | Only maintainers |

### Status Checks

Required status checks before merge:

```yaml
# Example lint/test workflow
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
        working-directory: client
      - run: npm run lint
        working-directory: client

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
        working-directory: client
      - run: npm test
        working-directory: client
```

---

## 8. Troubleshooting

### Common Issues

#### 1. AWS Credentials Error

```
Error: Unable to locate credentials
```

**Solution:** Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set correctly in repository secrets.

#### 2. AgentCore Deploy Fails

```
Error: Agent deployment failed
```

**Solutions:**
1. Check CloudWatch logs: `/aws/bedrock-agentcore/faiston_inventory_orchestration`
2. Verify `GOOGLE_API_KEY` is valid
3. Check for cold start timeout (30s limit)

#### 3. Terraform State Lock

```
Error: Error acquiring the state lock
```

**Solution:**
```bash
terraform force-unlock <LOCK_ID>
```

#### 4. S3 Sync Permission Denied

```
Error: Access Denied
```

**Solution:** Ensure IAM user has `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` permissions.

#### 5. CloudFront Invalidation Fails

```
Error: InvalidationBatch exceeds limit
```

**Solution:** Wait for previous invalidation to complete or use targeted paths instead of `/*`.

### Debug Mode

Enable debug logging in workflows:

```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

### Manual Deployment Commands

For emergency deployments (use with caution):

```bash
# Frontend (from client/)
npm run build
aws s3 sync out/ s3://faiston-one-frontend-prod --delete

# AgentCore (from server/agentcore-inventory/)
agentcore deploy --agent faiston_inventory_orchestration

# Terraform (from terraform/main/)
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

---

## Related Documentation

- [Infrastructure](INFRASTRUCTURE.md)
- [AgentCore Implementation Guide](AgentCore/IMPLEMENTATION_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md)

---

**Last Updated:** January 2026
**Platform:** Faiston NEXO
