# =============================================================================
# Terraform Configuration - Faiston One Frontend
# =============================================================================
# This configuration creates S3 + CloudFront + OIDC for GitHub Actions deploy
# Region: us-east-2 (Ohio)
# =============================================================================

terraform {
  # Requires 1.7.0+ for `removed` block support (orphaned state cleanup)
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.10"
    }
  }

  # Remote state backend - S3 with DynamoDB locking
  backend "s3" {
    bucket         = "faiston-terraform-state"
    key            = "faiston-one/terraform.tfstate"
    region         = "us-east-2"
    encrypt        = true
    dynamodb_table = "faiston-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Provider for CloudFront (must be us-east-1 for certificates)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}
