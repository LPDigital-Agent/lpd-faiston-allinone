# =============================================================================
# DynamoDB Table for SGA Human-in-the-Loop (HIL) Tasks
# =============================================================================
# Manages pending approval tasks and human oversight workflows.
#
# Key Design Principles:
# - Tasks are created when AI agents need human approval
# - Separate from main inventory table for:
#   - Independent scaling
#   - Faster queries on pending items
#   - Clear separation of concerns
#
# Task Types:
# - APPROVAL_NEW_PN    : New Part Number creation approval
# - APPROVAL_ENTRY     : High-value entry approval
# - APPROVAL_ADJUSTMENT: Inventory adjustment approval (ALWAYS HIL)
# - APPROVAL_DISCARD   : Asset discard/loss approval (ALWAYS HIL)
# - APPROVAL_TRANSFER  : Cross-project transfer approval
# - REVIEW_ENTRY       : Entry executed, pending review
# - ESCALATION         : Escalated issues
#
# Status Flow:
# PENDING -> APPROVED | REJECTED | EXPIRED
#
# Billing: PAY_PER_REQUEST (on-demand, serverless)
# TTL: Enabled for automatic cleanup of old resolved tasks
# =============================================================================

resource "aws_dynamodb_table" "sga_hil_tasks" {
  name         = "${var.project_name}-sga-hil-tasks-${var.environment}"
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
  # Auto-cleanup resolved tasks after retention period
  # Recommended: 90 days for APPROVED/REJECTED, 30 days for EXPIRED
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # =============================================================================
  # Point-in-time Recovery (PITR)
  # =============================================================================
  # Critical for audit trail and compliance
  point_in_time_recovery {
    enabled = true
  }

  # =============================================================================
  # Primary Key Attributes
  # =============================================================================
  # PK: TASK#{task_id}
  # SK: METADATA | COMMENT#{timestamp} | ATTACHMENT#{doc_id}

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # =============================================================================
  # GSI1: Tasks by Assignee
  # =============================================================================
  # Query pattern: Get all tasks assigned to a user
  # GSI1PK: ASSIGNEE#{user_id}
  # GSI1SK: {status}#{created_at}#{task_id}

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1-AssigneeQuery"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI2: Tasks by Status
  # =============================================================================
  # Query pattern: Get all pending tasks, sorted by priority/date
  # GSI2PK: STATUS#{status}
  # GSI2SK: {priority}#{created_at}#{task_id}

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
  # GSI3: Tasks by Type
  # =============================================================================
  # Query pattern: Get all tasks of a specific type
  # GSI3PK: TYPE#{task_type}
  # GSI3SK: {status}#{created_at}#{task_id}

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
  # GSI4: Tasks by Reference Entity
  # =============================================================================
  # Query pattern: Get all tasks related to an asset/movement/project
  # GSI4PK: REF#{entity_type}#{entity_id}
  # GSI4SK: {created_at}#{task_id}

  attribute {
    name = "GSI4PK"
    type = "S"
  }

  attribute {
    name = "GSI4SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI4-ReferenceQuery"
    hash_key        = "GSI4PK"
    range_key       = "GSI4SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # Tags
  # =============================================================================
  tags = {
    Name        = "Faiston SGA HIL Tasks"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Human-in-the-Loop"
    Description = "Pending approval tasks and human oversight workflows"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_hil_tasks_table_name" {
  description = "DynamoDB table name for SGA HIL Tasks"
  value       = aws_dynamodb_table.sga_hil_tasks.name
}

output "sga_hil_tasks_table_arn" {
  description = "DynamoDB table ARN for SGA HIL Tasks"
  value       = aws_dynamodb_table.sga_hil_tasks.arn
}
