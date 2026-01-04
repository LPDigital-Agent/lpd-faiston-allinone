# =============================================================================
# DynamoDB Table for SGA Audit Log
# =============================================================================
# Immutable audit trail for all inventory operations.
#
# Key Design Principles:
# - APPEND-ONLY: Records are never modified or deleted
# - COMPLETE HISTORY: Captures all actions by users and AI agents
# - COMPLIANCE: Meets LGPD and internal audit requirements
# - HIGH VOLUME: Optimized for write-heavy workload
#
# Event Types:
# - MOVEMENT_*    : Entry, exit, transfer, adjustment events
# - ASSET_*       : Asset creation, update, status change
# - TASK_*        : HIL task created, approved, rejected
# - AUTH_*        : Login, permission changes
# - AGENT_*       : AI agent decisions and confidence scores
# - SYSTEM_*      : System events, errors, warnings
#
# Security Features:
# - Deletion protection enabled
# - Point-in-time recovery enabled
# - No TTL (permanent retention)
#
# Billing: PAY_PER_REQUEST (on-demand, serverless)
# =============================================================================

resource "aws_dynamodb_table" "sga_audit_log" {
  name         = "${var.project_name}-sga-audit-log-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  # =============================================================================
  # ALWAYS enable deletion protection for audit logs
  # =============================================================================
  deletion_protection_enabled = true

  # =============================================================================
  # Point-in-time Recovery (PITR)
  # =============================================================================
  # MANDATORY for audit compliance
  point_in_time_recovery {
    enabled = true
  }

  # =============================================================================
  # NO TTL - Audit logs are retained permanently
  # =============================================================================
  # If data retention policy requires cleanup, use S3 Glacier archival instead

  # =============================================================================
  # Primary Key Attributes
  # =============================================================================
  # PK: LOG#{YYYY-MM-DD} (daily partitioning for efficient querying)
  # SK: {timestamp}#{event_id}

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # =============================================================================
  # GSI1: Events by Actor (User/Agent)
  # =============================================================================
  # Query pattern: Get all actions by a specific user or agent
  # GSI1PK: ACTOR#{actor_type}#{actor_id}
  # GSI1SK: {timestamp}#{event_id}

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1-ActorQuery"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI2: Events by Entity
  # =============================================================================
  # Query pattern: Get all events related to an asset, movement, or task
  # GSI2PK: ENTITY#{entity_type}#{entity_id}
  # GSI2SK: {timestamp}#{event_id}

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI2-EntityQuery"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI3: Events by Type
  # =============================================================================
  # Query pattern: Get all events of a specific type (for analysis)
  # GSI3PK: TYPE#{event_type}
  # GSI3SK: {timestamp}#{event_id}

  attribute {
    name = "GSI3PK"
    type = "S"
  }

  attribute {
    name = "GSI3SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI3-TypeQuery"
    hash_key        = "GSI3PK"
    range_key       = "GSI3SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI4: Events by Session
  # =============================================================================
  # Query pattern: Get all events in a user session (for debugging)
  # GSI4PK: SESSION#{session_id}
  # GSI4SK: {timestamp}#{event_id}

  attribute {
    name = "GSI4PK"
    type = "S"
  }

  attribute {
    name = "GSI4SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI4-SessionQuery"
    hash_key        = "GSI4PK"
    range_key       = "GSI4SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # Tags
  # =============================================================================
  tags = {
    Name        = "Faiston SGA Audit Log"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Audit Trail"
    Description = "Immutable audit log for inventory operations"
    Compliance  = "LGPD"
    Retention   = "Permanent"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_audit_log_table_name" {
  description = "DynamoDB table name for SGA Audit Log"
  value       = aws_dynamodb_table.sga_audit_log.name
}

output "sga_audit_log_table_arn" {
  description = "DynamoDB table ARN for SGA Audit Log"
  value       = aws_dynamodb_table.sga_audit_log.arn
}
