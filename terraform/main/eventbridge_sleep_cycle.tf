# =============================================================================
# EventBridge Rules for NEXO Mind Sleep Cycle
# =============================================================================
# Lei 4 (Respeito aos Ciclos): The "Sonhador" (Dreamer) consolidates memories.
#
# This module creates EventBridge rules to:
# 1. Trigger Sleep Cycle at 03:00 AM UTC (memory consolidation)
# 2. Trigger Daily Digest at 09:00 AM UTC (Ritual de Despertar)
#
# Architecture:
# EventBridge → Lambda → LearningAgent (A2A) → sleep_cycle tool
#
# GENESIS_KERNEL Laws Applied:
# - Lei 4: Consolidation is MANDATORY (cannot be disabled)
# - Lei 2: Master Memories need Tutor validation
# =============================================================================

# =============================================================================
# Local Variables
# =============================================================================

locals {
  # Sleep Cycle timing
  sleep_cycle_cron  = "cron(0 3 * * ? *)" # 03:00 AM UTC daily
  daily_digest_cron = "cron(0 9 * * ? *)" # 09:00 AM UTC daily (06:00 BRT)

  # LearningAgent runtime (the "Sonhador")
  learning_agent_id = "learning"
}

# =============================================================================
# Lambda Function for Sleep Cycle Trigger
# =============================================================================

data "archive_file" "sleep_cycle_lambda" {
  type        = "zip"
  output_path = "${path.module}/sleep_cycle_lambda.zip"

  source {
    content  = <<-EOF
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

def handler(event, context):
    """
    Sleep Cycle Trigger Lambda for NEXO Mind.

    Invokes the LearningAgent's sleep_cycle tool via A2A protocol.
    This implements Lei 4 (Respeito aos Ciclos) - consolidation is mandatory.

    Event types:
    - sleep_cycle: Memory consolidation (03:00 AM)
    - daily_digest: Morning summary (09:00 AM / 06:00 BRT)
    """
    action = event.get('action', 'sleep_cycle')
    dry_run = event.get('dry_run', False)
    session_id = event.get('session_id', f'scheduled-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}')

    print(f'[NEXO Mind] Starting {action} (dry_run={dry_run}, session={session_id})')

    url = os.environ.get('LEARNING_AGENT_URL')
    if not url:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'LEARNING_AGENT_URL not configured'})
        }

    try:
        # A2A JSON-RPC request to invoke the tool
        request_body = json.dumps({
            'jsonrpc': '2.0',
            'id': f'{action}-{session_id}',
            'method': 'tools/call',
            'params': {
                'name': action,
                'arguments': {
                    'dry_run': dry_run,
                    'session_id': session_id,
                }
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=request_body,
            headers={
                'Content-Type': 'application/json',
                'X-Sleep-Cycle': 'true',
                'X-Session-Id': session_id,
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=300) as response:  # 5min timeout for consolidation
            status = response.status
            body = response.read().decode('utf-8')
            result = json.loads(body) if body else {}

            print(f'[NEXO Mind] {action} completed: status={status}')
            print(f'[NEXO Mind] Result: {json.dumps(result, default=str)[:1000]}...')

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'action': action,
                    'success': True,
                    'session_id': session_id,
                    'result': result
                }, default=str)
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print(f'[NEXO Mind] HTTP error: {e.code} - {error_body}')
        return {
            'statusCode': e.code,
            'body': json.dumps({
                'action': action,
                'success': False,
                'error': f'HTTP {e.code}',
                'details': error_body[:500]
            })
        }
    except Exception as e:
        print(f'[NEXO Mind] Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'action': action,
                'success': False,
                'error': str(e)
            })
        }
EOF
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "sleep_cycle" {
  function_name = "${local.name_prefix}-nexo-sleep-cycle"
  description   = "NEXO Mind Sleep Cycle - Lei 4 (Respeito aos Ciclos) - Memory consolidation trigger"

  filename         = data.archive_file.sleep_cycle_lambda.output_path
  source_code_hash = data.archive_file.sleep_cycle_lambda.output_base64sha256
  handler          = "lambda_function.handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 300 # 5 minutes for consolidation
  memory_size      = 256

  role = aws_iam_role.sleep_cycle_lambda.arn

  environment {
    variables = {
      LOG_LEVEL          = var.environment == "prod" ? "INFO" : "DEBUG"
      LEARNING_AGENT_URL = "https://bedrock-agentcore.${var.aws_region}.amazonaws.com/runtimes/${aws_bedrockagentcore_agent_runtime.sga_agents[local.learning_agent_id].agent_runtime_id}/invocations/"
    }
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-nexo-sleep-cycle"
    Module  = "NEXO_MIND"
    Feature = "Sleep Cycle"
    Law     = "Lei 4 - Respeito aos Ciclos"
  })
}

# =============================================================================
# IAM Role for Sleep Cycle Lambda
# =============================================================================

resource "aws_iam_role" "sleep_cycle_lambda" {
  name = "${local.name_prefix}-sleep-cycle-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-sleep-cycle-lambda-role"
    Module  = "NEXO_MIND"
    Feature = "Sleep Cycle"
  })
}

# Basic Lambda execution permissions
resource "aws_iam_role_policy_attachment" "sleep_cycle_basic" {
  role       = aws_iam_role.sleep_cycle_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permission to invoke LearningAgent runtime
resource "aws_iam_role_policy" "sleep_cycle_agentcore" {
  name = "agentcore-invoke-learning"
  role = aws_iam_role.sleep_cycle_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgentRuntime",
        ]
        Resource = [
          aws_bedrockagentcore_agent_runtime.sga_agents[local.learning_agent_id].agent_runtime_arn
        ]
      }
    ]
  })
}

# =============================================================================
# EventBridge Rule - Sleep Cycle (03:00 AM UTC)
# =============================================================================

resource "aws_cloudwatch_event_rule" "sleep_cycle" {
  name                = "${local.name_prefix}-nexo-sleep-cycle"
  description         = "NEXO Mind Sleep Cycle - Lei 4 (Respeito aos Ciclos) - Memory consolidation at 03:00 AM UTC"
  schedule_expression = local.sleep_cycle_cron

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-sleep-cycle-rule"
    Module  = "NEXO_MIND"
    Feature = "Sleep Cycle"
    Law     = "Lei 4"
  })
}

resource "aws_cloudwatch_event_target" "sleep_cycle" {
  rule      = aws_cloudwatch_event_rule.sleep_cycle.name
  target_id = "nexo-sleep-cycle"
  arn       = aws_lambda_function.sleep_cycle.arn

  input = jsonencode({
    action     = "sleep_cycle"
    dry_run    = false
    session_id = "scheduled-sleep-cycle"
  })
}

resource "aws_lambda_permission" "sleep_cycle_eventbridge" {
  statement_id  = "AllowEventBridgeSleepCycle"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sleep_cycle.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sleep_cycle.arn
}

# =============================================================================
# EventBridge Rule - Daily Digest (09:00 AM UTC / 06:00 BRT)
# =============================================================================

resource "aws_cloudwatch_event_rule" "daily_digest" {
  name                = "${local.name_prefix}-nexo-daily-digest"
  description         = "NEXO Mind Daily Digest - Ritual de Despertar - Morning summary at 09:00 AM UTC (06:00 BRT)"
  schedule_expression = local.daily_digest_cron

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-daily-digest-rule"
    Module  = "NEXO_MIND"
    Feature = "Daily Digest"
    Law     = "Lei 4"
  })
}

resource "aws_cloudwatch_event_target" "daily_digest" {
  rule      = aws_cloudwatch_event_rule.daily_digest.name
  target_id = "nexo-daily-digest"
  arn       = aws_lambda_function.sleep_cycle.arn # Reuses same Lambda, different action

  input = jsonencode({
    action     = "memory_statistics" # For now, just get stats. Daily Digest tool to be added.
    dry_run    = false
    session_id = "scheduled-daily-digest"
  })
}

resource "aws_lambda_permission" "daily_digest_eventbridge" {
  statement_id  = "AllowEventBridgeDailyDigest"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sleep_cycle.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_digest.arn
}

# =============================================================================
# Outputs
# =============================================================================

output "sleep_cycle_lambda_arn" {
  description = "ARN of the Sleep Cycle Lambda function"
  value       = aws_lambda_function.sleep_cycle.arn
}

output "sleep_cycle_rule_arn" {
  description = "ARN of the EventBridge rule for Sleep Cycle (03:00 AM UTC)"
  value       = aws_cloudwatch_event_rule.sleep_cycle.arn
}

output "daily_digest_rule_arn" {
  description = "ARN of the EventBridge rule for Daily Digest (09:00 AM UTC)"
  value       = aws_cloudwatch_event_rule.daily_digest.arn
}
