# =============================================================================
# EventBridge Rule for Post-Import Equipment Enrichment
# =============================================================================
# Triggers the EnrichmentAgent when equipment data is imported to PostgreSQL.
# This enables automatic data enrichment using Tavily for specs/manuals/docs.
#
# Event Flow:
# 1. NexoImportAgent completes import to PostgreSQL
# 2. Agent publishes event to EventBridge (nexo.import / ImportCompleted)
# 3. EventBridge rule matches event pattern
# 4. EventBridge invokes EnrichmentAgent with event payload
# 5. EnrichmentAgent uses Tavily via Gateway to enrich equipment data
# 6. Enriched data stored in S3 Knowledge Repository
#
# Reference:
# - PRD: product-development/current-feature/PRD-tavily-enrichment.md
# - Event Schema: PRD Section 5.4
# =============================================================================

# =============================================================================
# EventBridge Event Bus (using default)
# =============================================================================
# Using the default event bus for simplicity. Custom event bus can be created
# if needed for isolation or cross-account scenarios.

data "aws_cloudwatch_event_bus" "default" {
  name = "default"
}

# =============================================================================
# EventBridge Rule: Import Completed
# =============================================================================
resource "aws_cloudwatch_event_rule" "import_completed" {
  name        = "${var.project_name}-import-completed"
  description = "Triggers equipment enrichment when import completes"

  event_bus_name = data.aws_cloudwatch_event_bus.default.name

  event_pattern = jsonencode({
    source      = ["nexo.import"]
    detail-type = ["ImportCompleted"]
    detail = {
      # Only trigger for successful imports with new items
      status = ["SUCCESS"]
    }
  })

  tags = {
    Name        = "NEXO Import Completed Rule"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
    Purpose     = "Trigger post-import enrichment workflow"
  }
}

# =============================================================================
# Dead Letter Queue (DLQ) for Failed Enrichment Triggers
# =============================================================================
resource "aws_sqs_queue" "enrichment_dlq" {
  name = "${var.project_name}-enrichment-dlq"

  # Retain failed messages for 14 days
  message_retention_seconds = 1209600

  # Allow visibility timeout for retry processing
  visibility_timeout_seconds = 300

  tags = {
    Name        = "Enrichment DLQ"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
    Purpose     = "Dead letter queue for failed enrichment triggers"
  }
}

# SQS policy to allow EventBridge to send failed events
resource "aws_sqs_queue_policy" "enrichment_dlq" {
  queue_url = aws_sqs_queue.enrichment_dlq.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgeSendMessage"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.enrichment_dlq.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.import_completed.arn
          }
        }
      }
    ]
  })
}

# =============================================================================
# IAM Role for EventBridge to Invoke AgentCore
# =============================================================================
resource "aws_iam_role" "eventbridge_enrichment" {
  name = "${var.project_name}-eventbridge-enrichment-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgeAssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "EventBridge Enrichment Role"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
  }
}

# Policy to invoke AgentCore Runtime (EnrichmentAgent)
resource "aws_iam_role_policy" "eventbridge_invoke_agentcore" {
  name = "${var.project_name}-eventbridge-invoke-agentcore"
  role = aws_iam_role.eventbridge_enrichment.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowAgentCoreInvoke"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgent"
        ]
        Resource = [
          # Allow invoking any agent in this account/region
          "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent-runtime/*"
        ]
      }
    ]
  })
}

# =============================================================================
# EventBridge Target: EnrichmentAgent (via AgentCore HTTP)
# =============================================================================
# NOTE: AgentCore agents are invoked via HTTP endpoint.
# The target configuration uses API destination for HTTP invocation.

# API Destination Connection (SigV4 auth for AgentCore)
resource "aws_cloudwatch_event_connection" "agentcore_enrichment" {
  name               = "${var.project_name}-agentcore-enrichment-connection"
  description        = "Connection to AgentCore for enrichment invocation"
  authorization_type = "AWS_IAM"

  # Note: AWS_IAM authorization handles SigV4 signing automatically
  auth_parameters {}
}

# API Destination for EnrichmentAgent
resource "aws_cloudwatch_event_api_destination" "enrichment_agent" {
  name                             = "${var.project_name}-enrichment-agent-destination"
  description                      = "API destination for EnrichmentAgent invocation"
  invocation_endpoint              = "https://bedrock-agentcore.${var.aws_region}.amazonaws.com/agent-runtime"
  http_method                      = "POST"
  invocation_rate_limit_per_second = 10
  connection_arn                   = aws_cloudwatch_event_connection.agentcore_enrichment.arn
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "enrichment_agent" {
  rule           = aws_cloudwatch_event_rule.import_completed.name
  event_bus_name = data.aws_cloudwatch_event_bus.default.name
  target_id      = "enrichment-agent"

  # Target: API Destination (EnrichmentAgent via AgentCore HTTP)
  arn      = aws_cloudwatch_event_api_destination.enrichment_agent.arn
  role_arn = aws_iam_role.eventbridge_enrichment.arn

  # Transform event to agent invocation format
  input_transformer {
    input_paths = {
      import_id       = "$.detail.import_id"
      equipment_count = "$.detail.equipment_count"
      new_items       = "$.detail.new_items"
      updated_items   = "$.detail.updated_items"
      timestamp       = "$.detail.timestamp"
      tenant_id       = "$.detail.tenant_id"
      user_id         = "$.detail.user_id"
    }

    # Format for AgentCore invocation
    input_template = <<-EOF
      {
        "agentName": "faiston_sga_enrichment",
        "input": {
          "task": "enrich_imported_equipment",
          "import_id": <import_id>,
          "equipment_count": <equipment_count>,
          "new_items": <new_items>,
          "updated_items": <updated_items>,
          "timestamp": <timestamp>,
          "tenant_id": <tenant_id>,
          "user_id": <user_id>
        }
      }
    EOF
  }

  # Dead letter queue for failed invocations
  dead_letter_config {
    arn = aws_sqs_queue.enrichment_dlq.arn
  }

  # Retry configuration
  retry_policy {
    maximum_event_age_in_seconds = 3600 # 1 hour
    maximum_retry_attempts       = 3
  }
}

# =============================================================================
# CloudWatch Alarm for Failed Enrichments
# =============================================================================
resource "aws_cloudwatch_metric_alarm" "enrichment_failures" {
  alarm_name          = "${var.project_name}-enrichment-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when enrichment failures exceed threshold"

  dimensions = {
    QueueName = aws_sqs_queue.enrichment_dlq.name
  }

  alarm_actions = [] # Add SNS topic ARN for alerting

  tags = {
    Name        = "Enrichment Failures Alarm"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
  }
}

# =============================================================================
# SSM Parameter for EventBridge Configuration
# =============================================================================
resource "aws_ssm_parameter" "enrichment_eventbridge_config" {
  name        = "/${var.project_name}/sga/enrichment/eventbridge-config"
  description = "EventBridge configuration for equipment enrichment"
  type        = "String"
  value = jsonencode({
    rule_name          = aws_cloudwatch_event_rule.import_completed.name
    rule_arn           = aws_cloudwatch_event_rule.import_completed.arn
    dlq_url            = aws_sqs_queue.enrichment_dlq.url
    event_source       = "nexo.import"
    event_detail_type  = "ImportCompleted"
    api_destination_id = aws_cloudwatch_event_api_destination.enrichment_agent.id
  })

  tags = {
    Name    = "${var.project_name}-enrichment-eventbridge-config"
    Module  = "Gestao de Ativos"
    Feature = "Equipment Enrichment"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "enrichment_rule_name" {
  description = "EventBridge rule name for import completion"
  value       = aws_cloudwatch_event_rule.import_completed.name
}

output "enrichment_rule_arn" {
  description = "EventBridge rule ARN"
  value       = aws_cloudwatch_event_rule.import_completed.arn
}

output "enrichment_dlq_url" {
  description = "Dead letter queue URL for failed enrichment triggers"
  value       = aws_sqs_queue.enrichment_dlq.url
}

output "enrichment_dlq_arn" {
  description = "Dead letter queue ARN"
  value       = aws_sqs_queue.enrichment_dlq.arn
}

# =============================================================================
# Event Publishing Example (for NexoImportAgent)
# =============================================================================
# Python code to publish ImportCompleted event from NexoImportAgent:
#
# import boto3
# import json
# from datetime import datetime
#
# events_client = boto3.client('events')
#
# response = events_client.put_events(
#     Entries=[
#         {
#             'Source': 'nexo.import',
#             'DetailType': 'ImportCompleted',
#             'Detail': json.dumps({
#                 'import_id': 'uuid-here',
#                 'equipment_count': 150,
#                 'new_items': ['serial1', 'serial2'],
#                 'updated_items': ['serial3'],
#                 'timestamp': datetime.utcnow().isoformat() + 'Z',
#                 'tenant_id': 'faiston',
#                 'user_id': 'user@faiston.com',
#                 'status': 'SUCCESS'
#             }),
#             'EventBusName': 'default'
#         }
#     ]
# )
# =============================================================================
