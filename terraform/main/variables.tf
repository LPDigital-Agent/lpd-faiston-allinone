# =============================================================================
# Variables - Faiston One
# =============================================================================

# =============================================================================
# Core Configuration
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

# =============================================================================
# Academy Configuration
# =============================================================================

variable "academy_dev_ports" {
  description = "Local development ports for Academy CORS configuration"
  type        = list(number)
  default     = [3000, 3001, 8080, 8081]
}

variable "academy_custom_domains" {
  description = "Custom domains for Academy (production, staging)"
  type        = list(string)
  default = [
    "https://faiston.com",
    "https://www.faiston.com"
  ]
}

# =============================================================================
# Academy AgentCore Configuration
# =============================================================================
# These values are set after first AgentCore deployment

variable "academy_agentcore_cli_role_name" {
  description = "Name of the AgentCore CLI-created execution role (set after first deployment)"
  type        = string
  default     = ""
}

variable "academy_agentcore_memory_id" {
  description = "AgentCore Memory ID for Academy (created during agent deployment)"
  type        = string
  default     = ""
}
