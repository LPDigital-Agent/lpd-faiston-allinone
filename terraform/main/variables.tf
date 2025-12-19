# =============================================================================
# Variables - Faiston One Frontend
# =============================================================================

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "faiston-one"
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
  default     = "LPDigital-Agent"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "lpd-faiston-allinone"
}
