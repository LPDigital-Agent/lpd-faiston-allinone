# =============================================================================
# KMS Key for SGA RDS Aurora Encryption
# =============================================================================
# Dedicated KMS key for encrypting Aurora PostgreSQL data at rest.
#
# Features:
# - Automatic key rotation (annual)
# - Deletion protection (7 day pending window)
# - Policy allows RDS service access
#
# Best Practice:
# Using a dedicated key (vs. aws/rds) provides:
# - Better audit trail in CloudTrail
# - Granular access control
# - Cross-region disaster recovery capability
# =============================================================================

resource "aws_kms_key" "sga_rds" {
  description             = "KMS key for SGA Aurora PostgreSQL encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "sga-rds-key-policy"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow RDS Service"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
            "kms:ViaService"    = "rds.${var.aws_region}.amazonaws.com"
          }
        }
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "${local.name_prefix}-sga-rds-key"
    Module      = "SGA"
    Feature     = "PostgreSQL Database"
    Description = "KMS key for Aurora PostgreSQL encryption"
  }
}

resource "aws_kms_alias" "sga_rds" {
  name          = "alias/${local.name_prefix}-sga-rds"
  target_key_id = aws_kms_key.sga_rds.key_id
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_rds_kms_key_id" {
  description = "KMS key ID for SGA RDS encryption"
  value       = aws_kms_key.sga_rds.key_id
}

output "sga_rds_kms_key_arn" {
  description = "KMS key ARN for SGA RDS encryption"
  value       = aws_kms_key.sga_rds.arn
}
