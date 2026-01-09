# =============================================================================
# DynamoDB Table for SGA Sessions
# =============================================================================
# Manages user sessions and agent interactions.
#
# Key Design Principles:
# - Track active user sessions with AI agents
# - Enable queries by user, agent type, and status
# - Auto-cleanup inactive sessions via TTL (30 days)
# - Support multi-agent session tracking
#
# Session States:
# - ACTIVE     : Session is currently in progress
# - IDLE       : Session is inactive but not expired
# - TERMINATED : Session was explicitly ended
# - EXPIRED    : Session expired via TTL
#
# Use Cases:
# - Track user interactions with different agent types
# - Monitor active sessions for capacity planning
# - Debug and audit session history
# - Resume interrupted sessions
#
# Billing: PAY_PER_REQUEST (on-demand, serverless)
# TTL: Enabled for automatic cleanup of inactive sessions (30 days)
# =============================================================================

resource "aws_dynamodb_table" "sga_sessions" {
  name         = "${var.project_name}-sga-sessions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  # =============================================================================
  # Enable deletion protection in production
  # =============================================================================
  deletion_protection_enabled = var.environment == "prod"

  # =============================================================================
  # TTL Configuration
  # =============================================================================
  # Auto-cleanup inactive sessions after 30 days
  # Sessions are marked with expiresAt timestamp upon creation/update
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  # =============================================================================
  # Point-in-time Recovery (PITR)
  # =============================================================================
  # Critical for audit trail and disaster recovery
  point_in_time_recovery {
    enabled = true
  }

  # =============================================================================
  # Primary Key Attributes
  # =============================================================================
  # PK: USER#{user_id}
  # SK: SESSION#{session_id}

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # =============================================================================
  # GSI1: Agent Type Queries
  # =============================================================================
  # Query pattern: Get all sessions for a specific agent type
  # GSI1PK: AGENT#{agent_type}
  # GSI1SK: {timestamp}

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1-AgentTypeQuery"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI2: Status Queries
  # =============================================================================
  # Query pattern: Get all sessions by status (e.g., all active sessions)
  # GSI2PK: STATUS#{status}
  # GSI2SK: {timestamp}

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI2-StatusQuery"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # Tags
  # =============================================================================
  tags = {
    Name        = "Faiston SGA Sessions"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Session Management"
    Description = "User sessions and agent interactions tracking"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_sessions_table_name" {
  description = "DynamoDB table name for SGA Sessions"
  value       = aws_dynamodb_table.sga_sessions.name
}

output "sga_sessions_table_arn" {
  description = "DynamoDB table ARN for SGA Sessions"
  value       = aws_dynamodb_table.sga_sessions.arn
}
