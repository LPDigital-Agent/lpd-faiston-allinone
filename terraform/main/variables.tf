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

# =============================================================================
# SGA PostgreSQL Configuration
# =============================================================================
# Variables for Aurora PostgreSQL Serverless v2 migration

variable "sga_vpc_cidr" {
  description = "CIDR block for SGA VPC (PostgreSQL database)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "sga_aurora_min_capacity" {
  description = "Minimum ACU capacity for Aurora Serverless v2 (0.5-128)"
  type        = number
  default     = 0.5
}

variable "sga_aurora_max_capacity" {
  description = "Maximum ACU capacity for Aurora Serverless v2 (0.5-128)"
  type        = number
  default     = 8.0
}

variable "sga_aurora_engine_version" {
  description = "Aurora PostgreSQL engine version"
  type        = string
  default     = "16.4"
}

variable "sga_rds_proxy_idle_timeout" {
  description = "Idle timeout in seconds for RDS Proxy connections"
  type        = number
  default     = 1800
}

# =============================================================================
# POSTAL Service Configuration
# =============================================================================
# Credentials for POSTAL API integration (inventory operations)
# Set via terraform.tfvars or environment variables (TF_VAR_postal_*)

variable "postal_usuario" {
  description = "POSTAL API username"
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER_SET_VIA_TFVARS"
}

variable "postal_token" {
  description = "POSTAL API authentication token"
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER_SET_VIA_TFVARS"
}

variable "postal_id_perfil" {
  description = "POSTAL API profile ID"
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER_SET_VIA_TFVARS"
}
