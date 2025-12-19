# =============================================================================
# DynamoDB Table for Academy Trainings (NEXO Tutor Feature)
# =============================================================================
# Single-table design for personalized training data:
# - Training metadata (title, status, user_id, tenant_id)
# - Content sources (documents, URLs, YouTube videos)
# - Consolidated content and AI-generated assets
#
# Schema Design:
# PK: TRAINING#{training_id}
# SK: METADATA | SOURCE#{source_id} | ASSET#{asset_type}
#
# GSI1: User's trainings sorted by creation date
# GSI2: Tenant's trainings (multi-tenant) sorted by status/date
#
# Billing: PAY_PER_REQUEST (on-demand, cost-effective for variable load)
# =============================================================================

resource "aws_dynamodb_table" "academy_trainings" {
  name         = "${var.project_name}-academy-trainings-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  # =============================================================================
  # Primary Key Attributes
  # =============================================================================

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # =============================================================================
  # GSI1 Attributes: User-based queries
  # =============================================================================
  # Query pattern: Get all trainings for a user, sorted by creation date
  # GSI1PK: USER#{user_id}
  # GSI1SK: {created_at}#{training_id}

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # =============================================================================
  # GSI2 Attributes: Tenant-based queries (multi-tenant support)
  # =============================================================================
  # Query pattern: Get all trainings for a tenant, filterable by status
  # GSI2PK: TENANT#{tenant_id}
  # GSI2SK: {status}#{created_at}#{training_id}

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  # =============================================================================
  # Global Secondary Indexes
  # =============================================================================

  # GSI1: Query trainings by user
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # GSI2: Query trainings by tenant (multi-tenant, status filtering)
  global_secondary_index {
    name            = "GSI2"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # Backup & Recovery
  # =============================================================================

  point_in_time_recovery {
    enabled = true
  }

  # =============================================================================
  # TTL Configuration (Optional: Auto-delete drafts after 30 days)
  # =============================================================================
  # Uncomment to enable TTL for draft trainings that are never completed
  # ttl {
  #   attribute_name = "expires_at"
  #   enabled        = true
  # }

  tags = {
    Name        = "Faiston Academy Custom Trainings"
    Environment = var.environment
    Feature     = "NEXO Tutor"
    Description = "Stores personalized training content and metadata"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "academy_trainings_table_name" {
  description = "DynamoDB table name for Academy Custom Trainings feature"
  value       = aws_dynamodb_table.academy_trainings.name
}

output "academy_trainings_table_arn" {
  description = "DynamoDB table ARN for Academy Custom Trainings feature"
  value       = aws_dynamodb_table.academy_trainings.arn
}
