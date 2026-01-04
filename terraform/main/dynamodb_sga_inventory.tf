# =============================================================================
# DynamoDB Table for SGA Inventory (Gestão de Estoque)
# =============================================================================
# Single-table design for inventory management with event sourcing pattern.
#
# Key Design Principles:
# - Movements (MOVE#) are immutable events (event sourcing)
# - Balances (BALANCE#) are projections calculated from movements
# - Reservations (RESERVE#) use TTL for automatic expiration
# - Assets (ASSET#) track serialized items with full lifecycle
#
# Entity Prefixes:
# - PN#       : Part Number catalog
# - ASSET#    : Serialized assets
# - LOC#      : Stock locations
# - BALANCE#  : Quantity projections
# - MOVE#     : Movement events (immutable)
# - RESERVE#  : Temporary reservations (with TTL)
# - TASK#     : Pending tasks/approvals
# - DIV#      : Divergences/anomalies
# - DOC#      : Documents/evidence (NFs, photos)
#
# Billing: PAY_PER_REQUEST (on-demand, serverless)
# Streams: Enabled for real-time projections and audit
# =============================================================================

resource "aws_dynamodb_table" "sga_inventory" {
  name         = "${var.project_name}-sga-inventory-${var.environment}"
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
  # - Real-time balance projections
  # - Audit trail
  # - Event notifications
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # =============================================================================
  # TTL Configuration
  # =============================================================================
  # Used for:
  # - Auto-expire reservations
  # - Cleanup temporary tasks
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # =============================================================================
  # Point-in-time Recovery (PITR)
  # =============================================================================
  # Critical for compliance and disaster recovery
  point_in_time_recovery {
    enabled = true
  }

  # =============================================================================
  # Primary Key Attributes
  # =============================================================================
  # PK: {ENTITY_TYPE}#{entity_id}
  # SK: {context}#{additional_key} | METADATA

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # =============================================================================
  # GSI1: Serial Number Lookup
  # =============================================================================
  # Query pattern: Find asset by serial number
  # GSI1PK: SERIAL#{serial_number}
  # GSI1SK: ASSET#{asset_id}

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1-SerialLookup"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI2: Location-based Queries
  # =============================================================================
  # Query pattern: Get all assets/balances at a location
  # GSI2PK: LOC#{location_id}
  # GSI2SK: {entity_type}#{entity_id}

  attribute {
    name = "GSI2PK"
    type = "S"
  }

  attribute {
    name = "GSI2SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI2-LocationQuery"
    hash_key        = "GSI2PK"
    range_key       = "GSI2SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI3: Project-based Queries
  # =============================================================================
  # Query pattern: Get all assets/movements for a project
  # GSI3PK: PROJ#{project_id}
  # GSI3SK: {entity_type}#{timestamp}#{entity_id}

  attribute {
    name = "GSI3PK"
    type = "S"
  }

  attribute {
    name = "GSI3SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI3-ProjectQuery"
    hash_key        = "GSI3PK"
    range_key       = "GSI3SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI4: Status-based Queries
  # =============================================================================
  # Query pattern: Get tasks by status, divergences by state
  # GSI4PK: STATUS#{status}
  # GSI4SK: {entity_type}#{timestamp}#{entity_id}

  attribute {
    name = "GSI4PK"
    type = "S"
  }

  attribute {
    name = "GSI4SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI4-StatusQuery"
    hash_key        = "GSI4PK"
    range_key       = "GSI4SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI5: Date-based Queries (Monthly Partitioning)
  # =============================================================================
  # Query pattern: Get movements by date range (monthly)
  # GSI5PK: DATE#{YYYY-MM}
  # GSI5SK: {timestamp}#{movement_id}

  attribute {
    name = "GSI5PK"
    type = "S"
  }

  attribute {
    name = "GSI5SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI5-DateQuery"
    hash_key        = "GSI5PK"
    range_key       = "GSI5SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # GSI6: Asset Timeline (Event Sourcing)
  # =============================================================================
  # Query pattern: Get complete history of an asset
  # GSI6PK: TIMELINE#{asset_id}
  # GSI6SK: {timestamp}#{event_type}#{event_id}

  attribute {
    name = "GSI6PK"
    type = "S"
  }

  attribute {
    name = "GSI6SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI6-AssetTimeline"
    hash_key        = "GSI6PK"
    range_key       = "GSI6SK"
    projection_type = "ALL"
  }

  # =============================================================================
  # Tags
  # =============================================================================
  tags = {
    Name        = "Faiston SGA Inventory"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Gestao de Estoque"
    Description = "Single-table design for inventory management with event sourcing"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_inventory_table_name" {
  description = "DynamoDB table name for SGA Inventory"
  value       = aws_dynamodb_table.sga_inventory.name
}

output "sga_inventory_table_arn" {
  description = "DynamoDB table ARN for SGA Inventory"
  value       = aws_dynamodb_table.sga_inventory.arn
}

output "sga_inventory_stream_arn" {
  description = "DynamoDB Stream ARN for SGA Inventory (for event-driven processing)"
  value       = aws_dynamodb_table.sga_inventory.stream_arn
}
