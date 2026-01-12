#!/usr/bin/env python3
"""
E2E Test: Smart Import CSV Expedition Requests (IAM Auth)
==========================================================
Tests the AgentCore flow for importing CSV files using IAM SigV4 auth.

This version uses IAM credentials (faiston-aio profile) instead of Cognito JWT.
The AgentCore runtime supports both auth methods.

Flow:
1. get_nf_upload_url → Get presigned S3 URL
2. PUT presigned URL → Upload file to S3
3. nexo_analyze_file → Analyze file structure
4. nexo_submit_answers → Answer clarification questions (if any)
5. nexo_execute_import → Execute import to PostgreSQL
6. Verify results

Author: Claude Code E2E Test
Date: January 2026
"""

import json
import os
import sys
import uuid
import requests
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from urllib.parse import quote

# =============================================================================
# Configuration
# =============================================================================

AWS_REGION = "us-east-2"
AWS_ACCOUNT_ID = "377311924364"
AWS_PROFILE = "faiston-aio"
AGENTCORE_ENDPOINT = f"https://bedrock-agentcore.{AWS_REGION}.amazonaws.com"
RUNTIME_ID = "faiston_asset_management-uSuLPsFQNH"
SGA_RUNTIME_ARN = f"arn:aws:bedrock-agentcore:{AWS_REGION}:{AWS_ACCOUNT_ID}:runtime/{RUNTIME_ID}"
CSV_FILE_PATH = "data/SOLICITAÇÕES DE EXPEDIÇÃO.csv"
TARGET_RECORD_COUNT = 1688

# =============================================================================
# AWS Session
# =============================================================================

def get_aws_session():
    """Get boto3 session with correct profile."""
    return boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)

def get_credentials():
    """Get AWS credentials for SigV4 signing."""
    session = get_aws_session()
    return session.get_credentials()

# =============================================================================
# AgentCore Invocation (using SigV4)
# =============================================================================

def invoke_agentcore(action: str, payload: dict, session_id: str = None) -> dict:
    """Invoke AgentCore using IAM SigV4 authentication."""

    # Build URL with encoded ARN
    encoded_arn = quote(SGA_RUNTIME_ARN, safe='')
    url = f"{AGENTCORE_ENDPOINT}/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

    # Build request body
    body = {"action": action, **payload}
    body_str = json.dumps(body)

    # Session ID for AgentCore (must be >= 33 characters)
    if not session_id:
        session_id = f"e2e-smart-import-iam-{uuid.uuid4().hex}"

    # Create AWS request for signing
    headers = {
        'Content-Type': 'application/json',
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': session_id,
    }

    # Sign request with SigV4
    request = AWSRequest(method='POST', url=url, data=body_str, headers=headers)
    credentials = get_credentials()
    SigV4Auth(credentials, 'bedrock-agentcore', AWS_REGION).add_auth(request)

    # Make request
    print(f"  → Invoking action: {action}")
    response = requests.post(
        url,
        headers=dict(request.headers),
        data=body_str,
        timeout=300
    )

    if response.status_code != 200:
        print(f"  ✗ Error {response.status_code}: {response.text[:500]}")
        raise Exception(f"AgentCore invocation failed: {response.status_code}")

    result = response.json()
    print(f"  ✓ Action {action} completed")
    return result, session_id

# =============================================================================
# E2E Test Steps
# =============================================================================

def step1_get_upload_url(filename: str):
    """Step 1: Get presigned URL for file upload."""
    print("\n" + "="*60)
    print("📤 STEP 1: Get Presigned Upload URL")
    print("="*60)

    result, session_id = invoke_agentcore('get_nf_upload_url', {
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
    """Step 3: Trigger NEXO file analysis."""
    print("\n" + "="*60)
    print("🤖 STEP 3: NEXO File Analysis")
    print("="*60)

    result, _ = invoke_agentcore('nexo_analyze_file', {
        's3_key': s3_key,
        'filename': filename,
    }, session_id)

    # Parse analysis result
    if not result.get('success', True):
        error = result.get('error', 'Unknown error')
        print(f"  ✗ Analysis failed: {error}")
        return None

    analysis = result.get('analysis', {})
    questions = result.get('questions', [])
    session_state = result.get('session_state', {})
    confidence = result.get('overall_confidence', 0)

    print(f"  Total rows: {analysis.get('total_rows', 'N/A')}")
    print(f"  Confidence: {confidence:.1%}" if isinstance(confidence, (int, float)) else f"  Confidence: {confidence}")
    print(f"  Questions: {len(questions)}")

    # Show column mappings
    mappings = result.get('column_mappings', [])
    if mappings:
        print("  Column mappings:")
        for m in mappings[:5]:
            conf = m.get('confidence', 0)
            conf_str = f"{conf:.0%}" if isinstance(conf, (int, float)) else str(conf)
            print(f"    {m.get('file_column', '?')} → {m.get('target_field', '?')} ({conf_str})")

    return {
        'session_state': session_state,
        'questions': questions,
        'analysis': analysis,
        'column_mappings': mappings
    }

def step4_submit_answers(session_state: dict, questions: list, session_id: str):
    """Step 4: Submit answers to clarification questions."""
    print("\n" + "="*60)
    print("❓ STEP 4: Answer Clarification Questions")
    print("="*60)

    if not questions:
        print("  No questions to answer - proceeding directly")
        return session_state

    # Auto-answer questions with first option (for E2E test)
    answers = {}
    for q in questions:
        q_id = q.get('id', '')
        options = q.get('options', [])
        if options:
            answers[q_id] = options[0].get('value', '')
            print(f"  Q: {q.get('question', '?')[:50]}...")
            print(f"    A: {answers[q_id]}")

    result, _ = invoke_agentcore('nexo_submit_answers', {
        'session_state': session_state,
        'answers': answers
    }, session_id)

    updated_state = result.get('session', session_state)
    ready = result.get('ready_for_processing', False)
    remaining = result.get('remaining_questions', [])

    print(f"  Ready for processing: {ready}")
    print(f"  Remaining questions: {len(remaining)}")

    # If more questions, recurse
    if remaining and len(remaining) > 0:
        return step4_submit_answers(updated_state, remaining, session_id)

    return updated_state

def step5_execute_import(session_state: dict, s3_key: str, filename: str,
                         column_mappings: list, session_id: str):
    """Step 5: Execute the import."""
    print("\n" + "="*60)
    print("⚡ STEP 5: Execute Import")
    print("="*60)

    # Convert column mappings to array format if dict
    if isinstance(column_mappings, dict):
        column_mappings = [
            {'file_column': k, 'target_field': v}
            for k, v in column_mappings.items()
        ]

    result, _ = invoke_agentcore('nexo_execute_import', {
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

def step6_verify_results():
    """Step 6: Verify results summary."""
    print("\n" + "="*60)
    print("🔍 STEP 6: Verify Results")
    print("="*60)

    # Try to get dashboard summary for verification
    try:
        result, _ = invoke_agentcore('get_dashboard_summary', {})
        if result:
            print(f"  Dashboard data retrieved")
            if 'total_assets' in result:
                print(f"    Total assets: {result.get('total_assets', 'N/A')}")
            if 'total_movements' in result:
                print(f"    Total movements: {result.get('total_movements', 'N/A')}")
    except Exception as e:
        print(f"  Note: Dashboard summary not available ({e})")

    print("  ✓ Verification step completed")
    print("  (Full DB verification requires direct PostgreSQL access)")

# =============================================================================
# Main
# =============================================================================

def main():
    print("\n" + "="*70)
    print("🚀 E2E TEST: Smart Import CSV Expedition Requests (IAM Auth)")
    print("="*70)
    print(f"File: {CSV_FILE_PATH}")
    print(f"Target records: {TARGET_RECORD_COUNT:,}")
    print(f"AgentCore Runtime: {RUNTIME_ID}")
    print(f"AWS Profile: {AWS_PROFILE}")
    print()

    # Check file exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, '..', CSV_FILE_PATH)

    if not os.path.exists(csv_path):
        # Try relative to cwd
        csv_path = CSV_FILE_PATH
        if not os.path.exists(csv_path):
            print(f"❌ File not found: {CSV_FILE_PATH}")
            sys.exit(1)

    # Count lines in CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        line_count = sum(1 for _ in f) - 1  # Subtract header
    print(f"CSV lines (excluding header): {line_count:,}")

    try:
        # Step 1: Get presigned URL
        upload_url, s3_key, session_id = step1_get_upload_url(
            os.path.basename(csv_path)
        )

        # Step 2: Upload file
        step2_upload_file(upload_url, csv_path)

        # Step 3: Analyze file
        analysis_result = step3_analyze_file(s3_key, os.path.basename(csv_path), session_id)

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
        step6_verify_results()

        # Summary
        print("\n" + "="*70)
        print("📊 E2E TEST SUMMARY")
        print("="*70)

        success = import_result.get('success', False)
        if success:
            print("✅ TEST PASSED - Import completed successfully")
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
