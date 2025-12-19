# =============================================================================
# SSM Parameter Store - Faiston Academy API Keys
# =============================================================================
# Secrets management using SSM Parameter Store (free tier)
# More cost-effective than Secrets Manager for static API keys
#
# IMPORTANT: Actual values must be set manually after deployment
# via AWS Console or CLI (see instructions below)
# =============================================================================

# =============================================================================
# Google API Key Parameter (for Gemini AI)
# =============================================================================
# Used by: All AI agents for content generation
# Set via CLI:
#   aws ssm put-parameter \
#     --name "/faiston-one/academy/google-api-key" \
#     --value "your-api-key-here" \
#     --type "SecureString" \
#     --overwrite

resource "aws_ssm_parameter" "academy_google_api_key" {
  name        = "/${var.project_name}/academy/google-api-key"
  description = "Google Gemini API key for Academy AI features"
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_VIA_CONSOLE_OR_CLI"

  # Lifecycle: ignore value changes (managed outside Terraform)
  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Name        = "Faiston Academy Google API Key"
    Environment = var.environment
    Feature     = "Academy AI"
    ManagedBy   = "terraform"
    Note        = "Value must be set manually via AWS Console or CLI"
  }
}

# =============================================================================
# ElevenLabs API Key Parameter (for TTS)
# =============================================================================
# Used by: AudioClassAgent for high-quality voice generation
# Set via CLI:
#   aws ssm put-parameter \
#     --name "/faiston-one/academy/elevenlabs-api-key" \
#     --value "your-api-key-here" \
#     --type "SecureString" \
#     --overwrite

resource "aws_ssm_parameter" "academy_elevenlabs_api_key" {
  name        = "/${var.project_name}/academy/elevenlabs-api-key"
  description = "ElevenLabs API key for Academy high-quality TTS"
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_VIA_CONSOLE_OR_CLI"

  # Lifecycle: ignore value changes (managed outside Terraform)
  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Name        = "Faiston Academy ElevenLabs API Key"
    Environment = var.environment
    Feature     = "AudioClass"
    ManagedBy   = "terraform"
    Note        = "Value must be set manually via AWS Console or CLI"
  }
}

# =============================================================================
# HeyGen API Key Parameter (for Video Generation)
# =============================================================================
# Used by: VideoClassAgent and ExtraClassAgent for AI avatar videos
# Set via CLI:
#   aws ssm put-parameter \
#     --name "/faiston-one/academy/heygen-api-key" \
#     --value "your-api-key-here" \
#     --type "SecureString" \
#     --overwrite

resource "aws_ssm_parameter" "academy_heygen_api_key" {
  name        = "/${var.project_name}/academy/heygen-api-key"
  description = "HeyGen API key for Academy AI avatar video generation"
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_VIA_CONSOLE_OR_CLI"

  # Lifecycle: ignore value changes (managed outside Terraform)
  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Name        = "Faiston Academy HeyGen API Key"
    Environment = var.environment
    Feature     = "VideoClass"
    ManagedBy   = "terraform"
    Note        = "Value must be set manually via AWS Console or CLI"
  }
}

# =============================================================================
# YouTube Data API v3 Key
# =============================================================================
# NOTE: YouTube API can use the same Google API key (google-api-key parameter)
# Ensure YouTube Data API v3 is enabled in Google Cloud Console for the key
# This separate parameter allows using a different key if needed

resource "aws_ssm_parameter" "academy_youtube_api_key" {
  name        = "/${var.project_name}/academy/youtube-api-key"
  description = "YouTube Data API v3 key for Academy video metadata"
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_VIA_CONSOLE_OR_CLI"

  # Lifecycle: ignore value changes (managed outside Terraform)
  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Name        = "Faiston Academy YouTube API Key"
    Environment = var.environment
    Feature     = "NEXO Tutor"
    ManagedBy   = "terraform"
    Note        = "Value must be set manually via AWS Console or CLI"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "academy_ssm_google_api_key_name" {
  description = "SSM Parameter name for Academy Google API Key"
  value       = aws_ssm_parameter.academy_google_api_key.name
}

output "academy_ssm_google_api_key_arn" {
  description = "SSM Parameter ARN for Academy Google API Key"
  value       = aws_ssm_parameter.academy_google_api_key.arn
}

output "academy_ssm_elevenlabs_api_key_name" {
  description = "SSM Parameter name for Academy ElevenLabs API Key"
  value       = aws_ssm_parameter.academy_elevenlabs_api_key.name
}

output "academy_ssm_elevenlabs_api_key_arn" {
  description = "SSM Parameter ARN for Academy ElevenLabs API Key"
  value       = aws_ssm_parameter.academy_elevenlabs_api_key.arn
}

output "academy_ssm_heygen_api_key_name" {
  description = "SSM Parameter name for Academy HeyGen API Key"
  value       = aws_ssm_parameter.academy_heygen_api_key.name
}

output "academy_ssm_heygen_api_key_arn" {
  description = "SSM Parameter ARN for Academy HeyGen API Key"
  value       = aws_ssm_parameter.academy_heygen_api_key.arn
}

output "academy_ssm_youtube_api_key_name" {
  description = "SSM Parameter name for Academy YouTube API Key"
  value       = aws_ssm_parameter.academy_youtube_api_key.name
}

output "academy_ssm_youtube_api_key_arn" {
  description = "SSM Parameter ARN for Academy YouTube API Key"
  value       = aws_ssm_parameter.academy_youtube_api_key.arn
}
