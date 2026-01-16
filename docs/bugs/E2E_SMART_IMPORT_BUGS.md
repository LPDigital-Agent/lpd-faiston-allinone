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

The E2E test script `e2e_smart_import_iam.py` uses IAM SigV4 authentication, but the AgentCore runtime `faiston_inventory_orchestration-uSuLPsFQNH` is configured with **JWT Authorizer (Cognito OAuth)**.

**Expected:** IAM SigV4 auth should work
**Actual:** Returns HTTP 403 with "Authorization method mismatch"

### Error Message

```
HTTP 403: {"message":"Authorization method mismatch. The agent is configured for a different authorization method than what was used in your request. Check the agent's authorization configuration and ensure your request uses the matching method (OAuth or SigV4)"}
```

### Root Cause Analysis

From `terraform/main/agentcore_gateway.tf` (lines 14-16):
```
# │ AgentCore RUNTIME (faiston_inventory_orchestration-uSuLPsFQNH)             │
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

## BUG-003: Invalid Model Identifier in Strands Agents (CRITICAL)

**Severity:** 🔴 CRITICAL (Blocks ALL A2A communication)
**Step:** STEP 3 - NEXO Analysis (inter-agent A2A call)
**Status:** ✅ **FIXED** (Code Changes Applied - 2026-01-12)

### Description

When the main SGA runtime delegates to specialist agents via A2A protocol, the target agents fail with an internal error because the model identifier is invalid.

**Expected:** Agent processes request and returns response
**Actual:** Agent returns JSON-RPC error `-32603` (Internal Error)

### Error Message (from CloudWatch logs)

```
botocore.errorfactory.ValidationException: An error occurred (ValidationException)
when calling the ConverseStream operation: The provided model identifier is invalid.
└ Bedrock region: us-east-2
└ Model id: litellm/gemini-3.0-pro
```

### Root Cause Analysis

1. **Agent code** (`server/agentcore-inventory/agents/*/main.py`) uses:
   ```python
   model=f"litellm/{MODEL_ID}"  # Results in "litellm/gemini-3.0-pro"
   ```

2. **Strands Framework** passes this model ID to **AWS Bedrock ConverseStream API**

3. **Bedrock** does NOT recognize `litellm/...` format - it expects:
   - Bedrock model IDs: `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - OR proper Strands model provider configuration

4. **LiteLLM** is a third-party model router, but requires proper configuration as a model provider in Strands

### Affected Components

| Component | Impact |
|-----------|--------|
| `faiston_sga_nexo_import` | ❌ Cannot process A2A requests |
| `faiston_sga_import` | ❌ Cannot process A2A requests |
| `faiston_sga_intake` | ❌ Cannot process A2A requests |
| `faiston_sga_learning` | ❌ Cannot process A2A requests |
| All 14 specialist agents | ❌ Cannot process A2A requests |

### CLAUDE.md Compliance

Per CLAUDE.md **§ LLM POLICY**:
> "ALL agents MUST use GEMINI 3.0 FAMILY as the LLM"

The intent is correct (use Gemini 3.0), but the **implementation** is broken.

### Resolution Options (Require PLAN MODE)

1. **Option A: Use Google AI Studio via LiteLLM (Original Intent)**
   - Configure LiteLLM as a proper model provider in Strands
   - Set `GOOGLE_API_KEY` environment variable in runtimes
   - Model ID: Keep `litellm/gemini-3.0-pro`

2. **Option B: Use Bedrock Models (AWS-native)**
   - Change model to Bedrock-supported: `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - **VIOLATES** CLAUDE.md "GEMINI 3.0 FAMILY ONLY" rule

3. **Option C: Use Gemini via Vertex AI in Strands**
   - Configure Vertex AI as model provider
   - Requires Google Cloud credentials in AgentCore runtimes

### Workaround

**NONE** - This is a fundamental architecture issue that blocks all A2A communication.

### ✅ Fix Applied (2026-01-12)

**Solution:** Use `strands.models.gemini.GeminiModel` class directly via Google AI Studio API.

**Changes Made:**

1. **`server/agentcore-inventory/agents/utils.py`** - Added centralized helper:
   ```python
   from strands.models.gemini import GeminiModel

   def create_gemini_model(agent_type: str = "default") -> GeminiModel:
       model_id = get_model(agent_type)
       params = {"temperature": 0.7, "max_output_tokens": 4096}
       if requires_thinking(agent_type):
           params["thinking_config"] = {"thinking_level": "high"}
       return GeminiModel(model_id=model_id, params=params)
   ```

2. **All 14 agent main.py files** - Updated model configuration:
   - **Before:** `model=f"litellm/{MODEL_ID}"` ❌
   - **After:** `model=create_gemini_model(AGENT_ID)` ✅

**Agents Updated:**
- carrier, compliance, equipment_research, estoque_control
- expedition, import, intake, learning
- nexo_import, observation, reconciliacao, reverse
- schema_evolution, validation

**Validation:** `validate_agents.py` passed for all 14 agents ✅

**Pending:** Deploy to AgentCore (GitHub Actions CI/CD)

### Evidence

CloudWatch Log Group: `/aws/bedrock-agentcore/runtimes/faiston_sga_nexo_import-0zNtFDAo7M-DEFAULT`
Timestamp: 2026-01-12T16:42:XX UTC

---

## Test Progress Summary

### Pre-Test Validation

| Check | Status | Details |
|-------|--------|---------|
| CSV file exists | ✅ Pass | 1,689 lines (1,688 + header) |
| AWS credentials | ✅ Pass | Account 377311924364, user github-actions |
| AgentCore runtime (main) | ✅ Pass | `faiston_inventory_orchestration-uSuLPsFQNH` with JWT auth |
| AgentCore A2A connectivity | ✅ Pass | SigV4 auth works for inter-agent calls |
| Agent model configuration | ✅ FIXED | Uses `GeminiModel` via Google AI Studio (pending deploy) |

### Test Execution

| Step | Status | Details |
|------|--------|---------|
| STEP 1: Get Upload URL | ✅ Pass | Works with JWT auth (Cognito) |
| STEP 2: Upload to S3 | ✅ Pass | File uploaded successfully |
| STEP 3: NEXO Analysis | ⏳ READY | BUG-003 fixed, awaiting deployment |
| STEP 4: Answer Questions | ⬜ Not Started | Awaiting Step 3 |
| STEP 5: Execute Import | ⬜ Not Started | Awaiting Step 3 |
| STEP 6: Verify Database | ⬜ Not Started | Awaiting Step 5 |

### Next Steps

1. ~~**PLAN MODE REQUIRED**: Fix BUG-003 (Model ID configuration)~~ ✅ **DONE**
2. Deploy updated agents to AgentCore (GitHub Actions CI/CD)
3. Re-run E2E test (`python scripts/e2e_smart_import_a2a.py`)
4. Verify 1,688 records in `pending_entry_items` table

---

## Acceptance Criteria Status

| # | Criterion | Status |
|---|-----------|--------|
| 1 | CSV file uploaded to S3 | ✅ Pass |
| 2 | NEXO analysis returns column mappings | ⏳ Ready (awaiting deploy) |
| 3 | All clarification questions answered | ⬜ Awaiting Step 3 |
| 4 | Import executes without fatal errors | ⬜ Awaiting Step 4 |
| 5 | 1,688 records in `pending_entry_items` | ⬜ Awaiting Step 5 |
| 6 | Serial numbers correctly mapped | ⬜ Awaiting Step 5 |
| 7 | Part numbers correctly mapped | ⬜ Awaiting Step 5 |
| 8 | Project IDs correctly mapped | ⬜ Awaiting Step 5 |
| 9 | No duplicate entries | ⬜ Awaiting Step 5 |
| 10 | CLAUDE.md rules not violated | ✅ Pass |

---

## Summary

**Test Status:** ⏳ **READY FOR DEPLOYMENT**

**Progress:** 2/6 steps completed (33%) - BUG-003 fixed, awaiting deployment

**Critical Issue:** ~~The Strands agents are configured with `litellm/gemini-3.0-pro` as model ID~~ ✅ **FIXED** - Now uses `GeminiModel` class directly.

**Required Action:**
1. ✅ ~~Enter PLAN MODE to fix model configuration~~ **DONE**
2. ⏳ Deploy updated agents via GitHub Actions
3. ⬜ Re-run E2E test
4. ⬜ Verify 1,688 records imported
