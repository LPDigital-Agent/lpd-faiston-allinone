# =============================================================================
# S3 Bucket for Academy Slides (SlideDeck Feature)
# =============================================================================
# Storage for AI-generated slide deck images (Imagen 3 + composition)
# Files are automatically deleted after 30 days via lifecycle policy
#
# Access: PUBLIC read (educational content is not sensitive)
# =============================================================================

# =============================================================================
# S3 Bucket
# =============================================================================

resource "aws_s3_bucket" "academy_slides" {
  bucket = "${var.project_name}-academy-slides-${var.environment}"

  tags = {
    Name        = "Faiston Academy Slides Storage"
    Environment = var.environment
    Feature     = "SlideDeck"
    Purpose     = "Storage for AI-generated slide deck images"
  }
}

# =============================================================================
# Bucket Configuration
# =============================================================================

# Allow public read access for slides (content is educational, not sensitive)
resource "aws_s3_bucket_public_access_block" "academy_slides" {
  bucket = aws_s3_bucket.academy_slides.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Bucket policy for public read access
resource "aws_s3_bucket_policy" "academy_slides_public_read" {
  bucket = aws_s3_bucket.academy_slides.id

  # Ensure public access block is applied first
  depends_on = [aws_s3_bucket_public_access_block.academy_slides]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.academy_slides.arn}/*"
      }
    ]
  })
}

# Server-side encryption (AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "academy_slides" {
  bucket = aws_s3_bucket.academy_slides.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy - delete files after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "academy_slides" {
  bucket = aws_s3_bucket.academy_slides.id

  rule {
    id     = "delete-old-slide-images"
    status = "Enabled"

    filter {
      prefix = "" # Apply to all objects
    }

    expiration {
      days = 30
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# CORS configuration for browser access
resource "aws_s3_bucket_cors_configuration" "academy_slides" {
  bucket = aws_s3_bucket.academy_slides.id

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

output "academy_slides_bucket_name" {
  description = "Name of the S3 bucket for Academy slide images"
  value       = aws_s3_bucket.academy_slides.id
}

output "academy_slides_bucket_arn" {
  description = "ARN of the S3 bucket for Academy slide images"
  value       = aws_s3_bucket.academy_slides.arn
}

output "academy_slides_bucket_url" {
  description = "Public URL base for Academy slide images"
  value       = "https://${aws_s3_bucket.academy_slides.id}.s3.${var.aws_region}.amazonaws.com"
}
