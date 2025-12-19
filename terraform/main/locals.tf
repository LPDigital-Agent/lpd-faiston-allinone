# =============================================================================
# Locals - Faiston One Frontend
# =============================================================================

locals {
  # Naming convention
  name_prefix = "${var.project_name}-${var.environment}"

  # Common tags for all resources
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = "${var.github_org}/${var.github_repo}"
  }

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
}
