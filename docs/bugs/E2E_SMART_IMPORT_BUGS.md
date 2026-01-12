# E2E Smart Import Test - Bug Documentation

**Test Date:** 2026-01-12
**Test Script:** `scripts/e2e_smart_import_iam.py`, `scripts/e2e_smart_import_a2a.py`
**Target File:** `data/SOLICITAÇÕES DE EXPEDIÇÃO.csv` (1,688 records)

---

## BUG-001: Authentication Method Mismatch (IAM vs OAuth)

**Severity:** High
**Step:** STEP 1 - Get Presigned Upload URL
**Status:** Open (Configuration Issue)

### Description

The E2E test script `e2e_smart_import_iam.py` uses IAM SigV4 authentication, but the AgentCore runtime `faiston_asset_management-uSuLPsFQNH` is configured with **JWT Authorizer (Cognito OAuth)**.

**Expected:** IAM SigV4 auth should work
**Actual:** Returns HTTP 403 with "Authorization method mismatch"

### Error Message

```
HTTP 403: {"message":"Authorization method mismatch. The agent is configured for a different authorization method than what was used in your request. Check the agent's authorization configuration and ensure your request uses the matching method (OAuth or SigV4)"}
```

### Root Cause Analysis

From `terraform/main/agentcore_gateway.tf` (lines 14-16):
```
# │ AgentCore RUNTIME (faiston_asset_management-uSuLPsFQNH)             │
# │ └─ JWT Authorizer ENABLED (customJWTAuthorizer)                     │
# │    - discoveryUrl: cognito-idp.../openid-configuration              │
```

The runtime was intentionally configured for JWT (Cognito) auth, not IAM auth, for security reasons (user-scoped access control).

### Resolution Options

1. **Use A2A script with Cognito credentials** (Recommended)
   - Set `E2E_TEST_USER_EMAIL` and `E2E_TEST_USER_PASSWORD` environment variables
   - Run `scripts/e2e_smart_import_a2a.py`

2. **Create dedicated IAM-auth test runtime** (Alternative)
   - Deploy a separate AgentCore runtime with IAM auth for CI/CD testing
   - Keep production runtime with JWT auth

### Workaround

Use the A2A script with Cognito test user `nexo-test@lpdigital.ai`:
```bash
export E2E_TEST_USER_EMAIL="nexo-test@lpdigital.ai"
export E2E_TEST_USER_PASSWORD="<password from SSM or user>"
python scripts/e2e_smart_import_a2a.py
```

---

## BUG-002: E2E Test Credentials Not Configured

**Severity:** Medium
**Step:** Pre-test Setup
**Status:** Open (Configuration Issue)

### Description

The E2E test scripts require Cognito credentials via environment variables, but these are not pre-configured in the development environment.

### Missing Configuration

- `E2E_TEST_USER_EMAIL` - Not set or empty
- `E2E_TEST_USER_PASSWORD` - Not set or empty

### Available Test User

From Cognito User Pool `us-east-2_lkBXr4kjy`:
- **Email:** `nexo-test@lpdigital.ai`
- **Username:** `61dbc5a0-8051-70b1-6c93-5d221b382a54`
- **Status:** CONFIRMED
- **Created:** 2026-01-06

### Proposed Fix

Store test credentials in AWS SSM Parameter Store:
```bash
aws ssm put-parameter \
  --name /faiston-one/e2e/test-user-email \
  --value "nexo-test@lpdigital.ai" \
  --type String \
  --profile faiston-aio --region us-east-2

aws ssm put-parameter \
  --name /faiston-one/e2e/test-user-password \
  --value "<password>" \
  --type SecureString \
  --profile faiston-aio --region us-east-2
```

Then update E2E scripts to fetch from SSM if env vars not set.

---

## Test Progress Summary

### Pre-Test Validation

| Check | Status | Details |
|-------|--------|---------|
| CSV file exists | ✅ Pass | 1,689 lines (1,688 + header) |
| AWS credentials | ✅ Pass | Account 377311924364, user github-actions |
| AgentCore runtime | ⚠️ Partial | Runtime exists, but requires JWT auth |

### Test Execution

| Step | Status | Details |
|------|--------|---------|
| STEP 1: Get Upload URL | ❌ Blocked | Auth mismatch (IAM vs OAuth) |
| STEP 2: Upload to S3 | ⬜ Not Started | Blocked by Step 1 |
| STEP 3: NEXO Analysis | ⬜ Not Started | Blocked by Step 1 |
| STEP 4: Answer Questions | ⬜ Not Started | Blocked by Step 1 |
| STEP 5: Execute Import | ⬜ Not Started | Blocked by Step 1 |
| STEP 6: Verify Database | ⬜ Not Started | Blocked by Step 1 |

### Next Steps

1. User provides Cognito password for `nexo-test@lpdigital.ai`
2. Set environment variables and re-run A2A script
3. If successful, update SSM with test credentials for CI/CD

---

## Acceptance Criteria Status

| # | Criterion | Status |
|---|-----------|--------|
| 1 | CSV file uploaded to S3 | ⬜ Blocked |
| 2 | NEXO analysis returns column mappings | ⬜ Blocked |
| 3 | All clarification questions answered | ⬜ Blocked |
| 4 | Import executes without fatal errors | ⬜ Blocked |
| 5 | 1,688 records in `pending_entry_items` | ⬜ Blocked |
| 6 | Serial numbers correctly mapped | ⬜ Blocked |
| 7 | Part numbers correctly mapped | ⬜ Blocked |
| 8 | Project IDs correctly mapped | ⬜ Blocked |
| 9 | No duplicate entries | ⬜ Blocked |
| 10 | CLAUDE.md rules not violated | ✅ Pass |
