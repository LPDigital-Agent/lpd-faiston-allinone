# =============================================================================
# S3 Bucket for SGA Documents (Gestão de Estoque)
# =============================================================================
# Storage for inventory documents, evidence, and NF files:
#
# Directory Structure:
# notas-fiscais/{YYYY}/{MM}/
# │   └── {nf_id}/
# │       ├── original.pdf         # Original NF PDF
# │       ├── original.xml         # Original NF XML
# │       ├── extraction.json      # AI-extracted data
# │       └── thumbnail.jpg        # Preview image
#
# evidences/{movement_id}/
# │   ├── photos/                  # Photos of equipment, packing
# │   ├── signatures/              # Digital signatures
# │   └── documents/               # Supporting documents
#
# inventories/{campaign_id}/
# │   ├── photos/                  # Counting photos
# │   └── exports/                 # Generated reports
#
# temp/uploads/                    # Temporary upload staging
#
# Security:
# - Private bucket, pre-signed URLs for document access
# - KMS encryption at rest
# - Versioning enabled for compliance
# - Lifecycle rules for cost optimization
# =============================================================================

# =============================================================================
# S3 Bucket
# =============================================================================

resource "aws_s3_bucket" "sga_documents" {
  bucket = "${var.project_name}-sga-documents-${var.environment}"

  tags = {
    Name        = "Faiston SGA Documents"
    Environment = var.environment
    Module      = "Gestao de Ativos"
    Feature     = "Gestao de Estoque"
    Purpose     = "NF files - evidence photos - inventory documents"
    Compliance  = "Fiscal"
  }
}

# =============================================================================
# Bucket Versioning (MANDATORY for fiscal documents)
# =============================================================================
# NF files and evidence must be versioned for compliance

resource "aws_s3_bucket_versioning" "sga_documents" {
  bucket = aws_s3_bucket.sga_documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

# =============================================================================
# Block Public Access (files accessed via pre-signed URLs only)
# =============================================================================

resource "aws_s3_bucket_public_access_block" "sga_documents" {
  bucket = aws_s3_bucket.sga_documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# Server-Side Encryption (KMS for sensitive fiscal data)
# =============================================================================

resource "aws_s3_bucket_server_side_encryption_configuration" "sga_documents" {
  bucket = aws_s3_bucket.sga_documents.id

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
# - Temp uploads deleted after 24 hours
# - NF files: Transition to IA after 90 days, Glacier after 2 years
# - Evidence: Keep for 5 years, then Glacier Deep Archive
# - Incomplete multipart uploads aborted after 7 days

resource "aws_s3_bucket_lifecycle_configuration" "sga_documents" {
  bucket = aws_s3_bucket.sga_documents.id

  # Rule 1: Delete temporary uploads after 24 hours
  rule {
    id     = "delete-temp-uploads"
    status = "Enabled"

    filter {
      prefix = "temp/"
    }

    expiration {
      days = 1
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }

  # Rule 2: NF storage tiering for cost optimization
  rule {
    id     = "nf-storage-tiering"
    status = "Enabled"

    filter {
      prefix = "notas-fiscais/"
    }

    # Move to Infrequent Access after 90 days
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 2 years (fiscal retention requirement)
    transition {
      days          = 730
      storage_class = "GLACIER"
    }

    # NFs must be retained for 5 years minimum (Brazilian fiscal law)
    # No expiration - permanent retention
  }

  # Rule 3: Evidence storage tiering
  rule {
    id     = "evidence-storage-tiering"
    status = "Enabled"

    filter {
      prefix = "evidences/"
    }

    # Move to Infrequent Access after 180 days
    transition {
      days          = 180
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 2 years
    transition {
      days          = 730
      storage_class = "GLACIER"
    }

    # Move to Deep Archive after 5 years
    transition {
      days          = 1825
      storage_class = "DEEP_ARCHIVE"
    }
  }

  # Rule 4: Inventory exports - short retention
  rule {
    id     = "inventory-exports-cleanup"
    status = "Enabled"

    filter {
      and {
        prefix = "inventories/"
        tags = {
          type = "export"
        }
      }
    }

    expiration {
      days = 90
    }
  }

  # Rule 5: Abort incomplete multipart uploads after 7 days
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Rule 6: Clean up old document versions after 365 days
  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

# =============================================================================
# CORS Configuration (for browser upload via pre-signed URLs)
# =============================================================================

resource "aws_s3_bucket_cors_configuration" "sga_documents" {
  bucket = aws_s3_bucket.sga_documents.id

  # GET: Download documents, photos
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = local.academy_cors_origins # Reusing same origins
    expose_headers  = ["Content-Length", "Content-Type", "ETag", "Content-Disposition"]
    max_age_seconds = 3600
  }

  # PUT: Upload documents, photos via pre-signed URL
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

output "sga_documents_bucket_name" {
  description = "Name of the S3 bucket for SGA documents"
  value       = aws_s3_bucket.sga_documents.id
}

output "sga_documents_bucket_arn" {
  description = "ARN of the S3 bucket for SGA documents"
  value       = aws_s3_bucket.sga_documents.arn
}

output "sga_documents_bucket_domain" {
  description = "Regional domain name for the SGA documents bucket"
  value       = aws_s3_bucket.sga_documents.bucket_regional_domain_name
}
