# =============================================================================
# S3 Bucket for Academy Generated Videos (VideoClass Feature)
# =============================================================================
# Storage for AI-generated videos (HeyGen avatars)
# Lifecycle: Auto-delete generated videos after 30 days
# Access: Pre-signed URLs only (no public access)
# =============================================================================

# =============================================================================
# S3 Bucket
# =============================================================================

resource "aws_s3_bucket" "academy_videos" {
  bucket = "${var.project_name}-academy-videos-${var.environment}"

  tags = {
    Name        = "Faiston Academy Videos"
    Environment = var.environment
    Feature     = "VideoClass"
    Purpose     = "Storage for AI-generated video content"
  }
}

# =============================================================================
# Bucket Configuration
# =============================================================================

# Block public access (files accessed via pre-signed URLs only)
resource "aws_s3_bucket_public_access_block" "academy_videos" {
  bucket = aws_s3_bucket.academy_videos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "academy_videos" {
  bucket = aws_s3_bucket.academy_videos.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versioning disabled - generated content doesn't need version history
resource "aws_s3_bucket_versioning" "academy_videos" {
  bucket = aws_s3_bucket.academy_videos.id

  versioning_configuration {
    status = "Disabled"
  }
}

# Lifecycle policy - delete generated videos after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "academy_videos" {
  bucket = aws_s3_bucket.academy_videos.id

  rule {
    id     = "delete-old-generated-videos"
    status = "Enabled"

    # Only apply to generated videos (not source materials)
    filter {
      prefix = "generated/"
    }

    expiration {
      days = 30
    }

    # Clean up incomplete multipart uploads after 7 days
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Rule for cleanup of temp/processing files
  rule {
    id     = "delete-temp-files"
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
}

# CORS configuration for browser access via pre-signed URLs
resource "aws_s3_bucket_cors_configuration" "academy_videos" {
  bucket = aws_s3_bucket.academy_videos.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = local.academy_cors_origins
    expose_headers  = ["Content-Length", "Content-Type", "ETag", "Content-Range"]
    max_age_seconds = 3600
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "academy_videos_bucket_name" {
  description = "Name of the S3 bucket for Academy generated videos"
  value       = aws_s3_bucket.academy_videos.id
}

output "academy_videos_bucket_arn" {
  description = "ARN of the S3 bucket for Academy generated videos"
  value       = aws_s3_bucket.academy_videos.arn
}

output "academy_videos_bucket_domain_name" {
  description = "Domain name of the S3 bucket for Academy generated videos"
  value       = aws_s3_bucket.academy_videos.bucket_domain_name
}
