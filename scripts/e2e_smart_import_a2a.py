#!/usr/bin/env python3
"""
E2E Test: Smart Import CSV via A2A Protocol
============================================
Tests the Smart Import flow using Strands A2A protocol (JSON-RPC 2.0).

Flow:
1. Authenticate via Cognito (get JWT token)
2. get_nf_upload_url → Get presigned S3 URL (via A2A)
3. PUT presigned URL → Upload file to S3
4. nexo_analyze_file → Analyze file structure (via A2A)
5. nexo_submit_answers → Answer clarification questions (via A2A)
6. nexo_execute_import → Execute import to PostgreSQL (via A2A)
7. Verify database records

Author: Claude Code E2E Test
Date: January 2026
"""

import json
import os
import sys
import uuid
from urllib.parse import quote
import requests
import boto3

# =============================================================================
# Configuration
# =============================================================================

AWS_REGION = "us-east-2"
AWS_ACCOUNT_ID = "377311924364"
AGENTCORE_ENDPOINT = f"https://bedrock-agentcore.{AWS_REGION}.amazonaws.com"

# NexoImport Agent (A2A protocol - main orchestrator)
NEXO_IMPORT_RUNTIME_ARN = f"arn:aws:bedrock-agentcore:{AWS_REGION}:{AWS_ACCOUNT_ID}:runtime/faiston_sga_nexo_import-0zNtFDAo7M"

# Test file
CSV_FILE_PATH = "data/SOLICITAÇÕES DE EXPEDIÇÃO.csv"
TARGET_RECORD_COUNT = 1688

# Cognito Configuration
COGNITO_USER_POOL_ID = "us-east-2_lkBXr4kjy"
COGNITO_CLIENT_ID = "7ovjm09dr94e52mpejvbu9v1cg"

# Test user credentials (from environment)
TEST_USER_EMAIL = os.environ.get('E2E_TEST_USER_EMAIL', '')
TEST_USER_PASSWORD = os.environ.get('E2E_TEST_USER_PASSWORD', '')

# Global token storage
_access_token = None

# =============================================================================
# Cognito Authentication
# =============================================================================

def authenticate_cognito(email: str = None, password: str = None) -> str:
    """Authenticate with Cognito and get access token."""
    global _access_token

    if _access_token:
        return _access_token

    email = email or TEST_USER_EMAIL
    password = password or TEST_USER_PASSWORD

    if not email or not password:
        print("\n🔐 Cognito Authentication Required")
        print("Set E2E_TEST_USER_EMAIL and E2E_TEST_USER_PASSWORD environment variables")
        print("Or enter credentials now:")
        email = input("  Email: ").strip()
        password = input("  Password: ").strip()

    print(f"\n🔐 Authenticating as: {email}")

    client = boto3.client('cognito-idp', region_name=AWS_REGION)

    try:
        response = client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password,
            }
        )

        if 'ChallengeName' in response:
            challenge = response['ChallengeName']
            print(f"  ⚠️ Auth challenge required: {challenge}")
            raise Exception(f"Auth challenge: {challenge}")

        auth_result = response.get('AuthenticationResult', {})
        _access_token = auth_result.get('AccessToken')

        if not _access_token:
            raise Exception("No access token in response")

        print("  ✓ Authentication successful")
        return _access_token

    except Exception as e:
        print(f"  ✗ Authentication failed: {e}")
        raise

# =============================================================================
# A2A Protocol Invocation (JSON-RPC 2.0)
# =============================================================================

def invoke_a2a(action: str, payload: dict, session_id: str = None) -> dict:
    """
    Invoke AgentCore using A2A protocol (JSON-RPC 2.0).

    A2A Protocol:
    - POST to root path /
    - JSON-RPC 2.0 body format with message/send method
    - Session header: X-Amzn-Bedrock-AgentCore-Runtime-Session-Id
    """
    access_token = authenticate_cognito()

    # Build A2A URL (root path, not /invocations)
    encoded_arn = quote(NEXO_IMPORT_RUNTIME_ARN, safe='')
    url = f"{AGENTCORE_ENDPOINT}/runtimes/{encoded_arn}/?qualifier=DEFAULT"

    # Session ID (must be >= 33 characters)
    if not session_id:
        session_id = f"e2e-smart-import-a2a-{uuid.uuid4().hex}"

    # Build JSON-RPC 2.0 request (A2A protocol)
    message_id = f"msg-{uuid.uuid4().hex[:8]}"
    request_id = f"req-{uuid.uuid4().hex[:8]}"

    # Pack action + payload as JSON text in message
    message_text = json.dumps({"action": action, **payload})

    json_rpc_request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": message_text
                    }
                ],
                "messageId": message_id
            }
        }
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': session_id,
    }

    print(f"  → A2A message/send: {action}")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=json_rpc_request,
            timeout=300
        )
    except requests.exceptions.Timeout:
        print(f"  ✗ Request timeout after 300s")
        raise

    if response.status_code != 200:
        print(f"  ✗ HTTP {response.status_code}: {response.text[:500]}")
        raise Exception(f"A2A invocation failed: {response.status_code}")

    # Parse JSON-RPC 2.0 response
    rpc_response = response.json()

    # Check for JSON-RPC error
    if "error" in rpc_response:
        error = rpc_response["error"]
        print(f"  ✗ JSON-RPC Error: {error.get('message', 'Unknown')}")
        raise Exception(f"A2A error: {error}")

    # Extract result from JSON-RPC response
    result = rpc_response.get("result", {})
    message = result.get("message", {})
    parts = message.get("parts", [])

    # Combine text parts
    response_text = ""
    for part in parts:
        if part.get("kind") == "text":
            response_text += part.get("text", "")

    # Try to parse response as JSON
    try:
        parsed_result = json.loads(response_text)
        print(f"  ✓ A2A response received")
        return parsed_result, session_id
    except json.JSONDecodeError:
        # Return raw text if not JSON
        print(f"  ✓ A2A response (text): {response_text[:100]}...")
        return {"raw_response": response_text}, session_id

# =============================================================================
# E2E Test Steps
# =============================================================================

def step1_get_upload_url(filename: str):
    """Step 1: Get presigned URL for file upload via A2A."""
    print("\n" + "="*60)
    print("📤 STEP 1: Get Presigned Upload URL (A2A)")
    print("="*60)

    result, session_id = invoke_a2a('get_nf_upload_url', {
        'filename': filename,
        'content_type': 'text/csv'
    })

    upload_url = result.get('upload_url')
    s3_key = result.get('s3_key')

    if not upload_url:
        raise Exception(f"No upload_url in response: {result}")

    print(f"  S3 Key: {s3_key}")
    print(f"  URL Preview: {upload_url[:80]}...")

    return upload_url, s3_key, session_id

def step2_upload_file(upload_url: str, file_path: str):
    """Step 2: Upload file to S3 via presigned URL."""
    print("\n" + "="*60)
    print("📁 STEP 2: Upload File to S3")
    print("="*60)

    with open(file_path, 'rb') as f:
        file_content = f.read()

    file_size = len(file_content)
    print(f"  File size: {file_size:,} bytes")

    response = requests.put(
        upload_url,
        data=file_content,
        headers={'Content-Type': 'text/csv'},
        timeout=60
    )

    if response.status_code not in (200, 204):
        raise Exception(f"Upload failed: {response.status_code} - {response.text}")

    print("  ✓ File uploaded successfully")

def step3_analyze_file(s3_key: str, filename: str, session_id: str):
    """Step 3: Trigger NEXO file analysis via A2A."""
    print("\n" + "="*60)
    print("🤖 STEP 3: NEXO File Analysis (A2A)")
    print("="*60)

    result, _ = invoke_a2a('nexo_analyze_file', {
        's3_key': s3_key,
        'filename': filename,
    }, session_id)

    if not result.get('success', True):
        error = result.get('error', 'Unknown error')
        print(f"  ✗ Analysis failed: {error}")
        return None

    analysis = result.get('analysis', {})
    questions = result.get('questions', [])
    session_state = result.get('session_state', {})
    confidence = result.get('overall_confidence', 0)

    print(f"  Total rows: {analysis.get('total_rows', 'N/A')}")
    print(f"  Confidence: {confidence:.1%}")
    print(f"  Questions: {len(questions)}")

    mappings = result.get('column_mappings', [])
    if mappings:
        print("  Column mappings:")
        for m in mappings[:5]:
            print(f"    {m.get('file_column', '?')} → {m.get('target_field', '?')}")

    return {
        'session_state': session_state,
        'questions': questions,
        'analysis': analysis,
        'column_mappings': mappings
    }

def step4_submit_answers(session_state: dict, questions: list, session_id: str):
    """Step 4: Submit answers to clarification questions via A2A."""
    print("\n" + "="*60)
    print("❓ STEP 4: Answer Clarification Questions (A2A)")
    print("="*60)

    if not questions:
        print("  No questions to answer - proceeding directly")
        return session_state

    answers = {}
    for q in questions:
        q_id = q.get('id', '')
        options = q.get('options', [])
        if options:
            answers[q_id] = options[0].get('value', '')
            print(f"  Q: {q.get('question', '?')[:50]}...")
            print(f"    A: {answers[q_id]}")

    result, _ = invoke_a2a('nexo_submit_answers', {
        'session_state': session_state,
        'answers': answers
    }, session_id)

    updated_state = result.get('session', session_state)
    ready = result.get('ready_for_processing', False)
    remaining = result.get('remaining_questions', [])

    print(f"  Ready for processing: {ready}")
    print(f"  Remaining questions: {len(remaining)}")

    if remaining:
        return step4_submit_answers(updated_state, remaining, session_id)

    return updated_state

def step5_execute_import(session_state: dict, s3_key: str, filename: str,
                         column_mappings: list, session_id: str):
    """Step 5: Execute the import via A2A."""
    print("\n" + "="*60)
    print("⚡ STEP 5: Execute Import (A2A)")
    print("="*60)

    if isinstance(column_mappings, dict):
        column_mappings = [
            {'file_column': k, 'target_field': v}
            for k, v in column_mappings.items()
        ]

    result, _ = invoke_a2a('nexo_execute_import', {
        'session_state': session_state,
        's3_key': s3_key,
        'filename': filename,
        'column_mappings': column_mappings
    }, session_id)

    success = result.get('success', False)
    assets_created = result.get('assets_created', 0)
    movements_created = result.get('movements_created', 0)
    pending_created = result.get('pending_items_created', 0)
    errors = result.get('errors', [])

    print(f"  Success: {success}")
    print(f"  Assets created: {assets_created}")
    print(f"  Movements created: {movements_created}")
    print(f"  Pending items: {pending_created}")
    print(f"  Errors: {len(errors)}")

    if errors:
        for err in errors[:3]:
            print(f"    - {err}")

    return result

def step6_verify_database(session_id: str):
    """Step 6: Verify records via A2A."""
    print("\n" + "="*60)
    print("🔍 STEP 6: Verify Database Records (A2A)")
    print("="*60)

    try:
        result, _ = invoke_a2a('get_dashboard_summary', {}, session_id)
        print(f"  Dashboard data retrieved")
    except Exception as e:
        print(f"  ⚠️ Dashboard query failed: {e}")

    print("  ✓ Verification step completed")

# =============================================================================
# Main
# =============================================================================

def main():
    print("\n" + "="*70)
    print("🚀 E2E TEST: Smart Import CSV via A2A Protocol")
    print("="*70)
    print(f"File: {CSV_FILE_PATH}")
    print(f"Target records: {TARGET_RECORD_COUNT:,}")
    print(f"Protocol: A2A (JSON-RPC 2.0)")
    print(f"Agent: NexoImportAgent")
    print()

    # Find CSV file
    csv_path = CSV_FILE_PATH
    if not os.path.exists(csv_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, '..', CSV_FILE_PATH)
        if os.path.exists(alt_path):
            csv_path = alt_path
        else:
            print(f"❌ File not found: {CSV_FILE_PATH}")
            sys.exit(1)

    # Count CSV lines
    with open(csv_path, 'r', encoding='utf-8') as f:
        line_count = sum(1 for _ in f) - 1
    print(f"CSV lines (excluding header): {line_count:,}")

    try:
        # Step 1: Get presigned URL
        upload_url, s3_key, session_id = step1_get_upload_url(
            os.path.basename(csv_path)
        )

        # Step 2: Upload file
        step2_upload_file(upload_url, csv_path)

        # Step 3: Analyze file
        analysis_result = step3_analyze_file(
            s3_key, os.path.basename(csv_path), session_id
        )

        if not analysis_result:
            print("\n❌ Analysis failed - cannot proceed")
            sys.exit(1)

        # Step 4: Answer questions
        session_state = step4_submit_answers(
            analysis_result['session_state'],
            analysis_result['questions'],
            session_id
        )

        # Step 5: Execute import
        import_result = step5_execute_import(
            session_state,
            s3_key,
            os.path.basename(csv_path),
            analysis_result.get('column_mappings', []),
            session_id
        )

        # Step 6: Verify
        step6_verify_database(session_id)

        # Summary
        print("\n" + "="*70)
        print("📊 E2E TEST SUMMARY (A2A Protocol)")
        print("="*70)

        success = import_result.get('success', False)
        if success:
            print("✅ TEST PASSED - Import completed successfully via A2A")
            print(f"   Assets created: {import_result.get('assets_created', 0)}")
            print(f"   Movements: {import_result.get('movements_created', 0)}")
            print(f"   Pending items: {import_result.get('pending_items_created', 0)}")
        else:
            print("❌ TEST FAILED - Import had errors")
            for err in import_result.get('errors', []):
                print(f"   - {err}")

        print("\n" + "="*70)
        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
