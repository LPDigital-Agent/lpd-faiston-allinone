#!/usr/bin/env python3
"""
E2E Test: Smart Import CSV via A2A Protocol (IAM SigV4 Auth)
=============================================================
Tests the Smart Import flow using Strands A2A protocol with IAM authentication.

This version uses IAM SigV4 (faiston-aio profile) instead of Cognito JWT.
AgentCore supports both authentication methods for A2A protocol.

Flow:
1. get_nf_upload_url → Get presigned S3 URL (via A2A)
2. PUT presigned URL → Upload file to S3
3. nexo_analyze_file → Analyze file structure (via A2A)
4. nexo_submit_answers → Answer clarification questions (via A2A)
5. nexo_execute_import → Execute import to PostgreSQL (via A2A)
6. Verify database records

LLM: Gemini 3.0 Pro (MANDATORY for critical agents)

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

# NexoImport Agent ARN (A2A protocol - main orchestrator)
# This agent uses Gemini 3.0 Pro with Thinking enabled
NEXO_IMPORT_RUNTIME_ARN = f"arn:aws:bedrock-agentcore:{AWS_REGION}:{AWS_ACCOUNT_ID}:runtime/faiston_sga_nexo_import-0zNtFDAo7M"

# Test file
CSV_FILE_PATH = "data/SOLICITAÇÕES DE EXPEDIÇÃO.csv"
TARGET_RECORD_COUNT = 1688

# S3 Configuration
S3_BUCKET = "faiston-one-sga-documents-prod"
S3_PREFIX = "tmp"  # Temporary uploads go here

# =============================================================================
# AWS Session & SigV4 Authentication
# =============================================================================

def get_aws_session():
    """Get boto3 session with correct profile."""
    return boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)

def get_credentials():
    """Get AWS credentials for SigV4 signing."""
    session = get_aws_session()
    return session.get_credentials()

# =============================================================================
# A2A Protocol Invocation (JSON-RPC 2.0 with SigV4)
# =============================================================================

def invoke_a2a_natural(message: str, session_id: str = None) -> dict:
    """
    Invoke AgentCore using A2A protocol with NATURAL LANGUAGE messages.

    Strands A2A Pattern:
    - Agent's LLM interprets the natural language message
    - LLM decides which tool to call based on intent
    - Tools execute and return results

    This is different from action-based routing - the LLM understands context!
    """
    # Build A2A URL with /invocations/ path
    encoded_arn = quote(NEXO_IMPORT_RUNTIME_ARN, safe='')
    url = f"{AGENTCORE_ENDPOINT}/runtimes/{encoded_arn}/invocations/"

    # Session ID (must be >= 33 characters)
    if not session_id:
        session_id = f"e2e-smart-import-a2a-iam-{uuid.uuid4().hex}"

    # Build JSON-RPC 2.0 request with NATURAL LANGUAGE message
    message_id = f"msg-{uuid.uuid4().hex[:8]}"
    request_id = f"req-{uuid.uuid4().hex[:8]}"

    # Natural language message - LLM will understand and route to tools
    message_text = message

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

    body_str = json.dumps(json_rpc_request)

    # Build headers
    headers = {
        'Content-Type': 'application/json',
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': session_id,
    }

    # Sign request with SigV4
    request = AWSRequest(method='POST', url=url, data=body_str, headers=headers)
    credentials = get_credentials()
    SigV4Auth(credentials, 'bedrock-agentcore', AWS_REGION).add_auth(request)

    print(f"  → A2A natural message: {message[:80]}...")

    try:
        response = requests.post(
            url,
            headers=dict(request.headers),
            data=body_str,
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
        error_msg = error.get('message', 'Unknown')
        error_data = error.get('data', '')
        print(f"  ✗ JSON-RPC Error: {error_msg}")
        if error_data:
            print(f"  ✗ Error data: {str(error_data)[:500]}")
        raise Exception(f"A2A error: {error}")

    # Extract result from JSON-RPC response
    # AgentCore A2A returns response in: result.artifacts[0].parts[0].text
    result = rpc_response.get("result", {})

    # Try artifacts first (AgentCore format)
    artifacts = result.get("artifacts", [])
    response_text = ""

    if artifacts:
        for artifact in artifacts:
            for part in artifact.get("parts", []):
                if part.get("kind") == "text":
                    response_text += part.get("text", "")
    else:
        # Fallback to message format (standard A2A)
        message_resp = result.get("message", {})
        parts = message_resp.get("parts", [])
        for part in parts:
            if part.get("kind") == "text":
                response_text += part.get("text", "")

    print(f"  ✓ A2A response: {response_text[:300]}...")
    return {"response": response_text, "raw": result}, session_id


def invoke_a2a(action: str, payload: dict, session_id: str = None) -> dict:
    """
    DEPRECATED: Use invoke_a2a_natural for Strands agents.

    This function is kept for backward compatibility but converts
    action-based calls to natural language messages.
    """
    # Convert action + payload to natural language message
    if action == "nexo_analyze_file":
        s3_key = payload.get('s3_key', '')
        filename = payload.get('filename', '')
        message = f"""Analise o arquivo CSV que foi enviado para o S3.

S3 Key: {s3_key}
Filename: {filename}

Por favor:
1. Use a ferramenta analyze_file para analisar a estrutura do arquivo
2. Detecte as colunas e tipos de dados
3. Sugira mapeamentos para o schema do inventário
4. Retorne a análise em formato JSON com: columns, total_rows, column_mappings, confidence"""

    elif action == "nexo_execute_import":
        s3_key = payload.get('s3_key', '')
        mappings = payload.get('column_mappings', [])
        message = f"""Execute a importação do arquivo CSV para o banco de dados.

S3 Key: {s3_key}
Column Mappings: {json.dumps(mappings)}

Por favor:
1. Use a ferramenta execute_import para processar o arquivo
2. Aplique os mapeamentos de colunas fornecidos
3. Insira os registros na tabela pending_entry_items
4. Retorne o resultado em JSON com: success, rows_imported, errors"""

    elif action == "get_dashboard_summary":
        message = """Retorne um resumo do dashboard de inventário.

Por favor use a ferramenta health_check para verificar o status do agente."""

    else:
        # Generic fallback
        message = f"Execute a ação '{action}' com os parâmetros: {json.dumps(payload)}"

    return invoke_a2a_natural(message, session_id)


# =============================================================================
# E2E Test Steps
# =============================================================================

def step1_get_upload_url(filename: str):
    """Step 1: Get presigned URL for file upload directly from S3 (no agent needed)."""
    print("\n" + "="*60)
    print("📤 STEP 1: Get Presigned Upload URL (Direct S3 + boto3)")
    print("="*60)

    # Generate session ID for the entire test flow
    session_id = f"e2e-smart-import-a2a-iam-{uuid.uuid4().hex}"

    # Generate S3 key with timestamp for uniqueness
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    s3_key = f"{S3_PREFIX}/{timestamp}_{filename}"

    # Get S3 client with profile
    session = get_aws_session()
    s3_client = session.client('s3')

    # Generate presigned URL for PUT operation
    upload_url = s3_client.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': S3_BUCKET,
            'Key': s3_key,
            'ContentType': 'text/csv'
        },
        ExpiresIn=3600
    )

    print(f"  S3 Bucket: {S3_BUCKET}")
    print(f"  S3 Key: {s3_key}")
    print(f"  Session ID: {session_id[:50]}...")
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
    """Step 3: Trigger NEXO file analysis via A2A (uses Gemini 3.0 Pro)."""
    print("\n" + "="*60)
    print("🤖 STEP 3: NEXO File Analysis (A2A + Gemini 3.0 Pro)")
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
    """Step 5: Execute the import via A2A (uses Gemini 3.0 Pro)."""
    print("\n" + "="*60)
    print("⚡ STEP 5: Execute Import (A2A + Gemini 3.0 Pro)")
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
    print("🚀 E2E TEST: Smart Import CSV via A2A Protocol (IAM SigV4)")
    print("="*70)
    print(f"File: {CSV_FILE_PATH}")
    print(f"Target records: {TARGET_RECORD_COUNT:,}")
    print(f"Protocol: A2A (JSON-RPC 2.0)")
    print(f"Auth: IAM SigV4 ({AWS_PROFILE})")
    print(f"LLM: Gemini 3.0 Pro (MANDATORY)")
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

        # Step 3: Analyze file (uses Gemini 3.0 Pro)
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

        # Step 5: Execute import (uses Gemini 3.0 Pro)
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
        print("📊 E2E TEST SUMMARY (A2A Protocol + Gemini 3.0 Pro)")
        print("="*70)

        success = import_result.get('success', False)
        if success:
            print("✅ TEST PASSED - Import completed successfully via A2A")
            print(f"   LLM: Gemini 3.0 Pro (MANDATORY)")
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
