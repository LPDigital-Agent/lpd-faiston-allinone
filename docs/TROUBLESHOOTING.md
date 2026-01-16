# Troubleshooting Guide - Faiston NEXO

Common issues and solutions for the Faiston NEXO AI-First platform.

## Table of Contents

1. [AgentCore Issues](#1-agentcore-issues)
2. [Authentication Issues](#2-authentication-issues)
3. [Database Issues](#3-database-issues)
4. [Frontend Issues](#4-frontend-issues)
5. [Deployment Issues](#5-deployment-issues)
6. [Performance Issues](#6-performance-issues)

---

## 1. AgentCore Issues

### HTTP 424 - Cold Start Timeout

**Symptom:**
```
HTTP 424 Failed Dependency
Error: Agent initialization exceeded 30 second limit
```

**Cause:** AgentCore has a **30-second cold start limit**. Heavy imports at module level cause timeout.

**Solution:**

1. **Check `agents/__init__.py`** - Should be empty or minimal:
```python
# BAD - imports everything at module load
from .estoque_control_agent import EstoqueControlAgent
from .intake_agent import IntakeAgent

# GOOD - empty file
# agents/__init__.py
# (leave empty - lazy load agents)
```

2. **Move imports inside handlers:**
```python
# BAD - heavy import at module level
from lxml import etree

# GOOD - lazy import inside handler
@app.action("process_nf")
async def handle_process_nf(request):
    from agents.intake_agent import IntakeAgent  # Lazy import
    agent = IntakeAgent()
    return await agent.run(request.payload)
```

3. **Use stdlib alternatives:**
```python
# BAD - heavy library
from bs4 import BeautifulSoup  # ~3s load time
from lxml import etree  # ~5s load time

# GOOD - stdlib
import xml.etree.ElementTree as ET  # instant
```

4. **Profile import time:**
```bash
time python -c "import your_module"
```

---

### HTTP 401 - Unauthorized

**Symptom:**
```
HTTP 401 Unauthorized
Error: Invalid or missing authorization token
```

**Causes & Solutions:**

1. **Expired JWT token:**
   - Check token expiration: `jwt.decode(token, options={"verify_signature": False})`
   - Implement token refresh in frontend

2. **Wrong Cognito client ID:**
   - Verify client ID: `7ovjm09dr94e52mpejvbu9v1cg`
   - Check `client/lib/config/agentcore.ts`

3. **Missing Bearer prefix:**
```typescript
// BAD
headers: { 'Authorization': token }

// GOOD
headers: { 'Authorization': `Bearer ${token}` }
```

4. **JWT Authorizer not configured:**
   - Check AgentCore runtime has JWT authorizer
   - Verify in GitHub Actions deploy workflow

---

### HTTP 502/503/504 - Gateway Errors

**Symptom:**
```
HTTP 502 Bad Gateway
HTTP 503 Service Unavailable
HTTP 504 Gateway Timeout
```

**Causes & Solutions:**

1. **Agent crash:**
   - Check CloudWatch Logs: `/aws/bedrock-agentcore/faiston_inventory_orchestration`
   - Look for Python exceptions

2. **Memory exceeded:**
   - Agent may have hit memory limit
   - Reduce payload size or optimize agent code

3. **Network timeout:**
   - Implement exponential backoff:
```typescript
async function invokeWithRetry(action: string, payload: unknown, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await sgaService.invoke(action, payload);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
    }
  }
}
```

---

### Connection Refused

**Symptom:**
```
Error: Connection refused
Error: ECONNREFUSED
```

**Causes & Solutions:**

1. **Wrong runtime ARN:**
   - Verify ARN in `client/lib/config/agentcore.ts`
   - Check runtime exists: `agentcore status --agent faiston_inventory_orchestration`

2. **Runtime not active:**
   - Status should be `ACTIVE`, not `CREATING` or `FAILED`
   - Wait for deployment to complete

3. **Wrong endpoint:**
   - Endpoint should be: `https://bedrock-agentcore.us-east-2.amazonaws.com`

---

## 2. Authentication Issues

### Login Fails Silently

**Symptom:** Login form submits but nothing happens, no error shown.

**Causes & Solutions:**

1. **Check browser console:**
   - Look for CORS errors
   - Look for network failures

2. **Verify Cognito configuration:**
```typescript
// client/services/authService.ts
const COGNITO_CONFIG = {
  userPoolId: 'us-east-2_lkBXr4kjy',  // Must match
  clientId: '7ovjm09dr94e52mpejvbu9v1cg',  // Must match
  region: 'us-east-2',
};
```

3. **Check user exists in Cognito:**
   - AWS Console → Cognito → User Pools → faiston-users-prod → Users

---

### Token Not Refreshing

**Symptom:** User gets logged out after ~1 hour.

**Solution:**

Implement token refresh before expiration:
```typescript
// Check token expiration and refresh if needed
function shouldRefreshToken(): boolean {
  const token = sessionStorage.getItem('accessToken');
  if (!token) return true;

  const payload = JSON.parse(atob(token.split('.')[1]));
  const expiresAt = payload.exp * 1000;
  const fiveMinutes = 5 * 60 * 1000;

  return Date.now() > expiresAt - fiveMinutes;
}
```

---

## 3. Database Issues

### Aurora Connection Timeout

**Symptom:**
```
Error: Connection timed out
Error: Can't connect to PostgreSQL server
```

**Causes & Solutions:**

1. **Aurora scaling from zero:**
   - Serverless v2 takes ~30s to scale from 0 ACU
   - First request after idle period will be slow

2. **Security group misconfigured:**
   - Lambda SG must have outbound to Aurora SG on port 5432
   - Aurora SG must have inbound from Lambda SG

3. **Use RDS Proxy:**
   - Always connect via RDS Proxy, not directly to Aurora
   - Proxy handles connection pooling and failover

---

### DynamoDB Throttling

**Symptom:**
```
ProvisionedThroughputExceededException
Error: Rate exceeded
```

**Note:** This is rare with on-demand billing mode.

**Solutions:**

1. **Verify billing mode:**
   - Should be `PAY_PER_REQUEST` (on-demand)
   - Check Terraform: `billing_mode = "PAY_PER_REQUEST"`

2. **Implement exponential backoff:**
```python
import time
from botocore.exceptions import ClientError

def dynamo_with_retry(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                time.sleep(2 ** attempt)
            else:
                raise
```

---

### GSI Projection Errors

**Symptom:**
```
Error: Attribute not found in projection
```

**Cause:** GSI only includes projected attributes.

**Solution:**

1. Check GSI projection in Terraform:
```hcl
global_secondary_index {
  name            = "GSI1"
  projection_type = "ALL"  # or "INCLUDE" with specific attributes
}
```

2. If using `INCLUDE`, ensure all needed attributes are listed.

---

## 4. Frontend Issues

### CORS Errors

**Symptom:**
```
Access-Control-Allow-Origin header missing
CORS policy blocked request
```

**Solution:**

1. **All CORS config is in `terraform/main/locals.tf`:**
```hcl
academy_cors_origins = concat(
  ["https://${aws_cloudfront_distribution.frontend.domain_name}"],
  var.academy_custom_domains,
  local.academy_cors_origins_dev,  # localhost ports
)
```

2. **Add development port if needed:**
   - Update `var.academy_dev_ports` in Terraform variables
   - Run `terraform apply`

3. **Never add CORS headers in Lambda or S3 manually** - centralized in Terraform.

---

### Page Not Found (404) After Refresh

**Symptom:** Direct URL access or page refresh returns 404.

**Cause:** SPA routing not configured in CloudFront.

**Solution:** Already configured in `terraform/main/locals.tf`:
```hcl
spa_error_responses = [
  {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
  },
  {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
  }
]
```

---

### State Not Persisting

**Symptom:** Data lost on page refresh.

**Solutions:**

1. **Use sessionStorage for auth:**
```typescript
sessionStorage.setItem('accessToken', token);
```

2. **Use TanStack Query for API data:**
   - Data is cached automatically
   - Configure `staleTime` and `gcTime`

3. **Use localStorage for user preferences:**
```typescript
localStorage.setItem('theme', 'dark');
```

---

## 5. Deployment Issues

### GitHub Actions Failing

**Symptom:** Deployment workflow fails.

**Common Causes:**

1. **Missing secrets:**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `GOOGLE_API_KEY`
   - `COGNITO_USER_POOL_ID`
   - `COGNITO_CLIENT_ID`

2. **Check workflow logs:**
   - GitHub → Actions → Select workflow run → View logs

3. **AgentCore CLI version:**
```yaml
- name: Install AgentCore CLI
  run: pip install bedrock-agentcore-starter-toolkit --quiet
```

---

### Terraform Plan Fails

**Symptom:** `terraform plan` shows errors.

**Common Solutions:**

1. **Initialize first:**
```bash
terraform init
```

2. **Check AWS credentials:**
```bash
aws sts get-caller-identity
```

3. **Check state lock:**
```bash
terraform force-unlock <LOCK_ID>
```

---

## 6. Performance Issues

### Slow Agent Responses

**Causes & Solutions:**

1. **Cold start:**
   - First request after idle is slow
   - Implement "keep-warm" strategy if needed

2. **Large payloads:**
   - Reduce request/response size
   - Stream large responses

3. **Complex LLM prompts:**
   - Optimize system prompts
   - Use smaller model for simple tasks

---

### High Memory Usage

**Symptom:** Agent OOM errors.

**Solutions:**

1. **Stream large data:**
   - Don't load entire files into memory
   - Process in chunks

2. **Clear references:**
```python
# Process and release
data = process_large_file()
result = extract_needed_info(data)
del data  # Release memory
```

---

## Quick Reference

### CloudWatch Log Groups

| Service | Log Group |
|---------|-----------|
| AgentCore Inventory | `/aws/bedrock-agentcore/faiston_inventory_orchestration` |
| AgentCore Academy | `/aws/bedrock-agentcore/faiston_academy_agents` |
| Lambda PostgreSQL Tools | `/aws/lambda/faiston-one-sga-postgres-tools-prod` |
| Aurora PostgreSQL | `/aws/rds/cluster/faiston-one-sga-postgres-prod/postgresql` |

### Useful Commands

```bash
# Check AgentCore status
agentcore status --agent faiston_inventory_orchestration

# View recent logs
aws logs tail /aws/bedrock-agentcore/faiston_inventory_orchestration --since 1h

# Check Aurora status
aws rds describe-db-clusters --db-cluster-identifier faiston-one-sga-postgres-prod

# List DynamoDB items
aws dynamodb scan --table-name faiston-one-sga-inventory-prod --max-items 10
```

---

## Related Documentation

- [AgentCore Implementation Guide](AgentCore/IMPLEMENTATION_GUIDE.md)
- [Infrastructure](INFRASTRUCTURE.md)
- [SGA Architecture](architecture/SGA_ESTOQUE_ARCHITECTURE.md)

---

**Last Updated:** January 2026
**Platform:** Faiston NEXO
