# =============================================================================
# DynamoDB Table for SGA Postings (Postagens de Envio)
# =============================================================================
# Single-table design for shipping postings management.
#
# Key Design Principles:
# - Main posting record (METADATA) stores current state
# - Event records (EVENT#) provide status history (event sourcing)
# - GSIs enable efficient queries by status (Kanban), user, and tracking code
#
# Entity Prefixes:
# - POSTING#    : Main posting record
# - STATUS#     : Status-based index (for Kanban)
# - USER#       : User-based index (creator queries)
# - TRACKING#   : Tracking code lookup
#
# Sort Key Patterns:
# - METADATA                    : Main posting record
# - EVENT#{timestamp}           : Status change events
#
# Status Values:
# - aguardando   : Awaiting shipment
# - em_transito  : In transit
# - entregue     : Delivered
# - cancelado    : Cancelled
#
# Billing: PAY_PER_REQUEST (on-demand, serverless)
# TTL: Optional cleanup of old completed postings (90 days after delivery)
# =============================================================================

resource "aws_dynamodb_table" "sga_postings" {
  name         = "${var.project_name}-sga-postings-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  # =============================================================================
  # Enable deletion protection in production
  # =============================================================================
  deletion_protection_enabled = var.environment == "prod"

  # =============================================================================
  # DynamoDB Streams for event-driven architecture
  # =============================================================================
  # NEW_AND_OLD_IMAGES provides full before/after state for:
  # - Real-time status notifications
  # - Audit trail
  # - Webhook triggers for tracking updates
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # =============================================================================
  # TTL Configuration
  # =============================================================================
  # Used for:
  # - Auto-cleanup of old completed postings (90 days after delivery)
  # - TTL attribute set when status becomes "entregue" or "cancelado"
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # =============================================================================
  # Point-in-time Recovery (PITR)
  # =============================================================================
  # Critical for compliance and disaster recovery
  point_in_time_recovery {
    enabled = var.environment == "prod"
  }

  # =============================================================================
  # Primary Key Attributes
  # =============================================================================
  # PK: POSTING#{posting_id}
  # SK: METADATA | EVENT#{timestamp}

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # =============================================================================
  # GSI1: Status-based Queries (Kanban Columns)
  # =============================================================================
  # Query pattern: Get all postings by status for Kanban board
  # GSI1PK: STATUS#{status}
  # GSI1SK: {created_at}#{posting_id}
  #
  # Example queries:
  # - Get all "aguardando" postings sorted by creation date
  # - Get all "em_transito" postings for dashboard

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1-StatusQuery"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI2: User-based Queries
  # =============================================================================
  # Query pattern: Get all postings created by a specific user
  # GSI2PK: USER#{user_id}
  # GSI2SK: {created_at}#{posting_id}
  #
  # Example queries:
  # - Get all postings created by user for "My Shipments" view
  # - Filter user's postings by date range

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI2-UserQuery"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI3: Tracking Code Lookup
  # =============================================================================
  # Query pattern: Find posting by carrier tracking code
  # GSI3PK: TRACKING#{tracking_code}
  # GSI3SK: POSTING#{posting_id}
  #
  # Example queries:
  # - Lookup posting when receiving tracking webhook from carrier
  # - Find posting by scanning tracking barcode

  attribute {
    name = "GSI3PK"
    type = "S"
  }

  attribute {
    name = "GSI3SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI3-TrackingLookup"
    hash_key        = "GSI3PK"
    range_key       = "GSI3SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # Tags
  # =============================================================================
  tags = {
    Name        = "Faiston SGA Postings"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Postagens de Envio"
    Description = "Single-table design for shipping postings with Kanban status tracking"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_postings_table_name" {
  description = "DynamoDB table name for SGA Postings"
  value       = aws_dynamodb_table.sga_postings.name
}

output "sga_postings_table_arn" {
  description = "DynamoDB table ARN for SGA Postings"
  value       = aws_dynamodb_table.sga_postings.arn
}

output "sga_postings_stream_arn" {
  description = "DynamoDB Stream ARN for SGA Postings (for event-driven processing)"
  value       = aws_dynamodb_table.sga_postings.stream_arn
}
