# =============================================================================
# S3 Bucket for SGA Equipment Documentation (Knowledge Base Source)
# =============================================================================
# Storage for equipment manuals, specifications, and datasheets.
# This bucket serves as the data source for Bedrock Knowledge Base.
#
# Directory Structure:
# manuals/{manufacturer}/{model}/
# │   ├── manual.pdf               # Equipment manual
# │   └── manual.pdf.metadata.json # Bedrock KB metadata
#
# specifications/{category}/
# │   └── {part_number}/
# │       ├── spec-sheet.pdf
# │       └── spec-sheet.pdf.metadata.json
#
# datasheets/by-part-number/{pn}/
# │   ├── datasheet.pdf
# │   ├── datasheet.pdf.metadata.json
# │   └── research-summary.md      # AI-generated summary
#
# research-logs/{YYYY-MM}/
# │   └── research-audit.jsonl     # Audit trail of research operations
#
# Security:
# - Private bucket, Bedrock KB accesses directly via IAM role
# - AES256 encryption at rest
# - Versioning enabled for document updates
# - Lifecycle rules for cost optimization
# =============================================================================

# =============================================================================
# S3 Bucket
# =============================================================================

resource "aws_s3_bucket" "sga_equipment_docs" {
  bucket = "${var.project_name}-sga-equipment-docs-${var.environment}"

  tags = {
    Name        = "Faiston SGA Equipment Documentation"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Gestao de Estoque - Knowledge Base"
    Purpose     = "Equipment manuals - specifications - datasheets for RAG"
    DataSource  = "Bedrock Knowledge Base"
  }
}

# =============================================================================
# Bucket Versioning (for document updates and rollback)
# =============================================================================

resource "aws_s3_bucket_versioning" "sga_equipment_docs" {
  bucket = aws_s3_bucket.sga_equipment_docs.id

  versioning_configuration {
    status = "Enabled"
  }
}

# =============================================================================
# Block Public Access (Bedrock KB accesses via IAM role only)
# =============================================================================

resource "aws_s3_bucket_public_access_block" "sga_equipment_docs" {
  bucket = aws_s3_bucket.sga_equipment_docs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# Server-Side Encryption
# =============================================================================

resource "aws_s3_bucket_server_side_encryption_configuration" "sga_equipment_docs" {
  bucket = aws_s3_bucket.sga_equipment_docs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# =============================================================================
# Lifecycle Rules
# =============================================================================
# - Research logs deleted after 90 days
# - Manuals transition to IA after 180 days (infrequent access)
# - Old versions cleaned up after 180 days
# - Incomplete uploads aborted after 3 days

resource "aws_s3_bucket_lifecycle_configuration" "sga_equipment_docs" {
  bucket = aws_s3_bucket.sga_equipment_docs.id

  # Rule 1: Delete research logs after 90 days
  rule {
    id     = "delete-research-logs"
    status = "Enabled"

    filter {
      prefix = "research-logs/"
    }

    expiration {
      days = 90
    }
  }

  # Rule 2: Transition manuals to Infrequent Access after 180 days
  rule {
    id     = "manuals-storage-tiering"
    status = "Enabled"

    filter {
      prefix = "manuals/"
    }

    transition {
      days          = 180
      storage_class = "STANDARD_IA"
    }

    # Manuals are kept indefinitely (reference documentation)
  }

  # Rule 3: Transition datasheets to Infrequent Access after 180 days
  rule {
    id     = "datasheets-storage-tiering"
    status = "Enabled"

    filter {
      prefix = "datasheets/"
    }

    transition {
      days          = 180
      storage_class = "STANDARD_IA"
    }
  }

  # Rule 4: Abort incomplete multipart uploads after 3 days
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 3
    }
  }

  # Rule 5: Clean up old document versions after 180 days
  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 180
    }
  }
}

# =============================================================================
# S3 Bucket Policy for Bedrock Knowledge Base Access
# =============================================================================
# Allow Bedrock service to read documents for KB ingestion

resource "aws_s3_bucket_policy" "sga_equipment_docs_bedrock" {
  bucket = aws_s3_bucket.sga_equipment_docs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowBedrockKBAccess"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.sga_equipment_docs.arn,
          "${aws_s3_bucket.sga_equipment_docs.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
          }
        }
      }
    ]
  })
}

# =============================================================================
# CORS Configuration (for browser download via pre-signed URLs)
# =============================================================================

resource "aws_s3_bucket_cors_configuration" "sga_equipment_docs" {
  bucket = aws_s3_bucket.sga_equipment_docs.id

  # GET: Download documents via pre-signed URL (for NexoCopilot citations)
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = local.academy_cors_origins # Reusing same origins
    expose_headers  = ["Content-Length", "Content-Type", "ETag", "Content-Disposition"]
    max_age_seconds = 3600
  }

  # PUT: Upload documents (for EquipmentResearchAgent)
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = local.academy_cors_origins # Reusing same origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_equipment_docs_bucket_name" {
  description = "Name of the S3 bucket for SGA equipment documentation"
  value       = aws_s3_bucket.sga_equipment_docs.id
}

output "sga_equipment_docs_bucket_arn" {
  description = "ARN of the S3 bucket for SGA equipment documentation"
  value       = aws_s3_bucket.sga_equipment_docs.arn
}

output "sga_equipment_docs_bucket_domain" {
  description = "Regional domain name for the SGA equipment docs bucket"
  value       = aws_s3_bucket.sga_equipment_docs.bucket_regional_domain_name
}
