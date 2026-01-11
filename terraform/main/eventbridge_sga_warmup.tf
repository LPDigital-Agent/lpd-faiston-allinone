# =============================================================================
# EventBridge Rules for SGA Agent Warm-Up
# =============================================================================
# AgentCore runtimes go idle after 15 minutes of inactivity, causing cold
# starts on next invocation. This module creates EventBridge rules to
# ping high-traffic agents every 10 minutes to keep them warm.
#
# Critical Agents (HIGH_TRAFFIC_AGENTS from shared/keep_alive.py):
# - nexo_import: Main orchestrator, highest traffic
# - intake: NF processing, frequent imports
# - estoque_control: Core inventory operations
# - learning: Memory operations, called by nexo_import
# - validation: Schema validation, called frequently
#
# Reference:
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-lifecycle.html
# =============================================================================

# =============================================================================
# Local Variables
# =============================================================================

locals {
  # Agents that benefit from staying warm (high-traffic)
  high_traffic_agents = [
    "nexo_import",
    "intake",
    "estoque_control",
    "learning",
    "validation",
  ]

  # Warm-up interval (10 minutes = 600 seconds, provides 5-minute buffer)
  warmup_interval_minutes = 10
}

# =============================================================================
# Lambda Function for Agent Warm-Up
# =============================================================================
# A simple Lambda that sends a health check ping to each agent

data "archive_file" "warmup_lambda" {
  type        = "zip"
  output_path = "${path.module}/warmup_lambda.zip"

  source {
    content  = <<-EOF
import json
import os
import urllib.request
import urllib.error

def handler(event, context):
    """
    Warm-up Lambda for AgentCore Runtimes.

    Sends a lightweight health check request to each agent to prevent
    the 15-minute idle timeout from causing cold starts.
    """
    results = []

    for agent_id in event.get('agent_ids', []):
        url = os.environ.get(f'AGENT_URL_{agent_id.upper()}')
        if not url:
            results.append({
                'agent_id': agent_id,
                'success': False,
                'error': 'URL not configured'
            })
            continue

        try:
            # Simple JSON-RPC health check (A2A protocol)
            request_body = json.dumps({
                'jsonrpc': '2.0',
                'id': f'warmup-{agent_id}',
                'method': 'health/check',
                'params': {}
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=request_body,
                headers={
                    'Content-Type': 'application/json',
                    'X-Warmup-Request': 'true',
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.status
                results.append({
                    'agent_id': agent_id,
                    'success': status == 200,
                    'status': status
                })

        except urllib.error.HTTPError as e:
            # Even 4xx responses keep the runtime warm
            results.append({
                'agent_id': agent_id,
                'success': True,  # Still warmed the runtime
                'status': e.code,
                'note': 'HTTP error but runtime warmed'
            })
        except Exception as e:
            results.append({
                'agent_id': agent_id,
                'success': False,
                'error': str(e)
            })

    print(f'Warm-up results: {json.dumps(results)}')
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Warm-up completed',
            'results': results
        })
    }
EOF
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "sga_warmup" {
  function_name = "${local.name_prefix}-sga-agent-warmup"
  description   = "Keeps high-traffic AgentCore runtimes warm to prevent cold starts"

  filename         = data.archive_file.warmup_lambda.output_path
  source_code_hash = data.archive_file.warmup_lambda.output_base64sha256
  handler          = "lambda_function.handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 60
  memory_size      = 128

  role = aws_iam_role.sga_warmup_lambda.arn

  # Agent URLs as environment variables
  environment {
    variables = merge(
      {
        LOG_LEVEL = var.environment == "prod" ? "INFO" : "DEBUG"
      },
      {
        for agent_id in local.high_traffic_agents :
        "AGENT_URL_${upper(agent_id)}" => "https://bedrock-agentcore.${var.aws_region}.amazonaws.com/runtimes/${aws_bedrockagentcore_agent_runtime.sga_agents[agent_id].agent_runtime_id}/invocations/"
      }
    )
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-sga-agent-warmup"
    Module  = "SGA"
    Feature = "Agent Warm-Up"
  })
}

# =============================================================================
# IAM Role for Warm-Up Lambda
# =============================================================================

resource "aws_iam_role" "sga_warmup_lambda" {
  name = "${local.name_prefix}-sga-warmup-lambda"

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
    Name    = "${local.name_prefix}-sga-warmup-lambda-role"
    Module  = "SGA"
    Feature = "Agent Warm-Up"
  })
}

# Basic Lambda execution permissions
resource "aws_iam_role_policy_attachment" "sga_warmup_basic" {
  role       = aws_iam_role.sga_warmup_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permission to invoke AgentCore runtimes
resource "aws_iam_role_policy" "sga_warmup_agentcore" {
  name = "agentcore-invoke"
  role = aws_iam_role.sga_warmup_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgentRuntime",
        ]
        Resource = [
          for agent_id in local.high_traffic_agents :
          aws_bedrockagentcore_agent_runtime.sga_agents[agent_id].agent_runtime_arn
        ]
      }
    ]
  })
}

# =============================================================================
# EventBridge Rule - Every 10 Minutes
# =============================================================================

resource "aws_cloudwatch_event_rule" "sga_warmup" {
  name                = "${local.name_prefix}-sga-agent-warmup"
  description         = "Triggers agent warm-up every ${local.warmup_interval_minutes} minutes to prevent cold starts"
  schedule_expression = "rate(${local.warmup_interval_minutes} minutes)"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-sga-warmup-rule"
    Module  = "SGA"
    Feature = "Agent Warm-Up"
  })
}

resource "aws_cloudwatch_event_target" "sga_warmup" {
  rule      = aws_cloudwatch_event_rule.sga_warmup.name
  target_id = "sga-agent-warmup"
  arn       = aws_lambda_function.sga_warmup.arn

  input = jsonencode({
    agent_ids = local.high_traffic_agents
  })
}

resource "aws_lambda_permission" "sga_warmup_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sga_warmup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sga_warmup.arn
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_warmup_lambda_arn" {
  description = "ARN of the agent warm-up Lambda function"
  value       = aws_lambda_function.sga_warmup.arn
}

output "sga_warmup_rule_arn" {
  description = "ARN of the EventBridge rule for agent warm-up"
  value       = aws_cloudwatch_event_rule.sga_warmup.arn
}
