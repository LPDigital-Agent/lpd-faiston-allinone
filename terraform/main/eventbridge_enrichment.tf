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
# EventBridge Target: CloudWatch Logs (Monitoring & Audit)
# =============================================================================
# NOTE: EventBridge API Destinations do NOT support AWS_IAM/SigV4 auth.
# Valid authorization_type values: BASIC, OAUTH_CLIENT_CREDENTIALS, API_KEY
#
# Current Architecture:
# - EventBridge captures ImportCompleted events for audit/monitoring
# - EnrichmentAgent is invoked via orchestrator routing (manual/API trigger)
# - Future: Lambda intermediary can invoke AgentCore with SigV4 if needed

# CloudWatch Log Group for import events
resource "aws_cloudwatch_log_group" "import_events" {
  name              = "/aws/events/${var.project_name}/import-completed"
  retention_in_days = 30

  tags = {
    Name        = "Import Completed Events"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Equipment Enrichment"
  }
}

# EventBridge Target: CloudWatch Logs (for monitoring)
resource "aws_cloudwatch_event_target" "import_logs" {
  rule           = aws_cloudwatch_event_rule.import_completed.name
  event_bus_name = data.aws_cloudwatch_event_bus.default.name
  target_id      = "import-logs"

  # Target: CloudWatch Logs
  arn = aws_cloudwatch_log_group.import_events.arn
}

# EventBridge Target: DLQ (for failed events)
resource "aws_cloudwatch_event_target" "enrichment_dlq" {
  rule           = aws_cloudwatch_event_rule.import_completed.name
  event_bus_name = data.aws_cloudwatch_event_bus.default.name
  target_id      = "enrichment-dlq"

  # Target: SQS DLQ (for later processing/retry)
  arn = aws_sqs_queue.enrichment_dlq.arn

  # Dead letter queue for this target itself
  dead_letter_config {
    arn = aws_sqs_queue.enrichment_dlq.arn
  }

  # Retry configuration
  retry_policy {
    maximum_event_age_in_seconds = 86400 # 24 hours
    maximum_retry_attempts       = 5
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
    rule_name         = aws_cloudwatch_event_rule.import_completed.name
    rule_arn          = aws_cloudwatch_event_rule.import_completed.arn
    dlq_url           = aws_sqs_queue.enrichment_dlq.url
    log_group         = aws_cloudwatch_log_group.import_events.name
    event_source      = "nexo.import"
    event_detail_type = "ImportCompleted"
    # Note: Direct AgentCore invocation via EventBridge not supported (no AWS_IAM auth)
    # EnrichmentAgent is invoked via orchestrator routing instead
    trigger_method = "orchestrator"
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
