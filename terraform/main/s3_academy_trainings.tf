# =============================================================================
# S3 Bucket for Academy Training Documents (NEXO Tutor Feature)
# =============================================================================
# Storage for user-uploaded content and AI-generated assets:
#
# Directory Structure:
# trainings/{training_id}/
# ├── documents/{version}/        # Uploaded PDFs, DOCs, TXT files
# ├── transcription.txt           # Consolidated text content
# ├── thumbnails/                 # AI-generated thumbnails
# │   ├── original.jpg
# │   ├── 400x600.jpg
# │   └── 200x300.jpg
# └── metadata.json               # Training metadata cache
#
# temp/uploads/                   # Temporary upload staging
#
# Security: Private bucket, pre-signed URLs for document access
# Lifecycle: Temp uploads deleted after 24 hours
# =============================================================================

# =============================================================================
# S3 Bucket
# =============================================================================

resource "aws_s3_bucket" "academy_trainings" {
  bucket = "${var.project_name}-academy-trainings-${var.environment}"

  tags = {
    Name        = "Faiston Academy Training Documents"
    Environment = var.environment
    Feature     = "NEXO Tutor"
    Purpose     = "User-uploaded documents and AI-generated training assets"
  }
}

# =============================================================================
# Bucket Versioning (for document history)
# =============================================================================

resource "aws_s3_bucket_versioning" "academy_trainings" {
  bucket = aws_s3_bucket.academy_trainings.id

  versioning_configuration {
    status = "Enabled"
  }
}

# =============================================================================
# Block Public Access (files accessed via pre-signed URLs only)
# =============================================================================

resource "aws_s3_bucket_public_access_block" "academy_trainings" {
  bucket = aws_s3_bucket.academy_trainings.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# Server-Side Encryption
# =============================================================================

resource "aws_s3_bucket_server_side_encryption_configuration" "academy_trainings" {
  bucket = aws_s3_bucket.academy_trainings.id

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
# - Old versions cleaned after 30 days
# - Incomplete multipart uploads aborted after 7 days

resource "aws_s3_bucket_lifecycle_configuration" "academy_trainings" {
  bucket = aws_s3_bucket.academy_trainings.id

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

  # Rule 2: Clean up old document versions after 30 days
  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    filter {
      prefix = "trainings/"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  # Rule 3: Abort incomplete multipart uploads after 7 days
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# =============================================================================
# CORS Configuration (for browser upload via pre-signed URLs)
# =============================================================================

resource "aws_s3_bucket_cors_configuration" "academy_trainings" {
  bucket = aws_s3_bucket.academy_trainings.id

  # GET: Download documents, thumbnails
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = local.academy_cors_origins
    expose_headers  = ["Content-Length", "Content-Type", "ETag", "Content-Disposition"]
    max_age_seconds = 3600
  }

  # PUT: Upload documents via pre-signed URL
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = local.academy_cors_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "academy_trainings_bucket_name" {
  description = "Name of the S3 bucket for Academy training documents"
  value       = aws_s3_bucket.academy_trainings.id
}

output "academy_trainings_bucket_arn" {
  description = "ARN of the S3 bucket for Academy training documents"
  value       = aws_s3_bucket.academy_trainings.arn
}

output "academy_trainings_bucket_domain" {
  description = "Regional domain name for the Academy trainings bucket"
  value       = aws_s3_bucket.academy_trainings.bucket_regional_domain_name
}
