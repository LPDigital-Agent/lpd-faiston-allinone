# =============================================================================
# Locals - Faiston One
# =============================================================================
# Centralized local values for shared configurations
# =============================================================================

# Get current AWS account ID dynamically
data "aws_caller_identity" "current" {}

locals {
  # =============================================================================
  # Naming Convention
  # =============================================================================
  name_prefix = "${var.project_name}-${var.environment}"

  # =============================================================================
  # Common Tags
  # =============================================================================
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = "${var.github_org}/${var.github_repo}"
  }

  # =============================================================================
  # Frontend Configuration
  # =============================================================================

  # S3 bucket name (must be globally unique)
  frontend_bucket_name = "${local.name_prefix}-frontend"

  # CloudFront settings
  s3_origin_id = "${local.name_prefix}-s3-origin"

  # SPA routing - custom error responses for client-side routing
  spa_error_responses = [
    {
      error_code            = 403
      response_code         = 200
      response_page_path    = "/index.html"
      error_caching_min_ttl = 10
    },
    {
      error_code            = 404
      response_code         = 200
      response_page_path    = "/index.html"
      error_caching_min_ttl = 10
    }
  ]

  # =============================================================================
  # Academy CORS Configuration
  # =============================================================================
  # CORS origins for Academy S3 buckets (audio, slides, videos, trainings)
  # Allows access from localhost dev ports and production CloudFront

  # Development origins (localhost with configured ports)
  academy_cors_origins_dev = [
    for port in var.academy_dev_ports : "http://localhost:${port}"
  ]

  # Development origins (127.0.0.1 variants)
  academy_cors_origins_loopback = [
    for port in var.academy_dev_ports : "http://127.0.0.1:${port}"
  ]

  # Combined CORS origins for Academy
  # Includes CloudFront domain and localhost development
  academy_cors_origins = concat(
    [
      "https://${aws_cloudfront_distribution.frontend.domain_name}"
    ],
    var.academy_custom_domains,
    local.academy_cors_origins_dev,
    local.academy_cors_origins_loopback
  )

  # =============================================================================
  # Academy Resource References
  # =============================================================================
  # These are passed to AgentCore as environment variables

  academy_trainings_bucket_name = aws_s3_bucket.academy_trainings.id
  academy_trainings_table_name  = aws_dynamodb_table.academy_trainings.name
  academy_audio_bucket_name     = aws_s3_bucket.academy_audio.id
  academy_slides_bucket_name    = aws_s3_bucket.academy_slides.id
  academy_videos_bucket_name    = aws_s3_bucket.academy_videos.id

  # =============================================================================
  # SGA Resource References (Gestao de Ativos - Estoque)
  # =============================================================================
  # These are passed to AgentCore as environment variables

  sga_inventory_table_name  = aws_dynamodb_table.sga_inventory.name
  sga_hil_tasks_table_name  = aws_dynamodb_table.sga_hil_tasks.name
  sga_audit_log_table_name  = aws_dynamodb_table.sga_audit_log.name
  sga_documents_bucket_name = aws_s3_bucket.sga_documents.id
}
