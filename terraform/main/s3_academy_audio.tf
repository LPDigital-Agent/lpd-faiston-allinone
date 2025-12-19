# =============================================================================
# S3 Bucket for Academy Audio Files (AudioClass Feature)
# =============================================================================
# Temporary storage for AI-generated audio (ElevenLabs TTS)
# Files are automatically deleted after 24 hours via lifecycle policy
#
# Access: Pre-signed URLs only (no public access)
# =============================================================================

# =============================================================================
# S3 Bucket
# =============================================================================

resource "aws_s3_bucket" "academy_audio" {
  bucket = "${var.project_name}-academy-audio-${var.environment}"

  tags = {
    Name        = "Faiston Academy Audio Storage"
    Environment = var.environment
    Feature     = "AudioClass"
    Purpose     = "Temporary storage for AI-generated audio files"
  }
}

# =============================================================================
# Bucket Configuration
# =============================================================================

# Block public access (files accessed via pre-signed URLs only)
resource "aws_s3_bucket_public_access_block" "academy_audio" {
  bucket = aws_s3_bucket.academy_audio.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "academy_audio" {
  bucket = aws_s3_bucket.academy_audio.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy - delete files after 24 hours
resource "aws_s3_bucket_lifecycle_configuration" "academy_audio" {
  bucket = aws_s3_bucket.academy_audio.id

  rule {
    id     = "delete-old-audio-files"
    status = "Enabled"

    filter {
      prefix = "audio/"
    }

    expiration {
      days = 1
    }

    # Also clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# CORS configuration for browser access via pre-signed URLs
resource "aws_s3_bucket_cors_configuration" "academy_audio" {
  bucket = aws_s3_bucket.academy_audio.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = local.academy_cors_origins
    expose_headers  = ["Content-Length", "Content-Type", "ETag"]
    max_age_seconds = 3600
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "academy_audio_bucket_name" {
  description = "Name of the S3 bucket for Academy audio files"
  value       = aws_s3_bucket.academy_audio.id
}

output "academy_audio_bucket_arn" {
  description = "ARN of the S3 bucket for Academy audio files"
  value       = aws_s3_bucket.academy_audio.arn
}
