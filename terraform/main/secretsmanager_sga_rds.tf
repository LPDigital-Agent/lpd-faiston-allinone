# =============================================================================
# Secrets Manager for SGA RDS Aurora Credentials
# =============================================================================
# Stores master database credentials for Aurora PostgreSQL.
# RDS Proxy uses these credentials for IAM authentication.
#
# Architecture:
# - Secret stores master username/password
# - RDS Proxy retrieves credentials via IAM role
# - Lambda connects to RDS Proxy using IAM auth (no password)
#
# Security:
# - Automatic rotation every 30 days
# - KMS encryption with dedicated key
# - VPC endpoint access only
# =============================================================================

# =============================================================================
# Master Database Secret
# =============================================================================

resource "random_password" "sga_rds_master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "sga_rds_master" {
  name        = "${local.name_prefix}-sga-rds-master"
  description = "Master credentials for SGA Aurora PostgreSQL cluster"
  kms_key_id  = aws_kms_key.sga_rds.arn

  tags = {
    Name        = "${local.name_prefix}-sga-rds-master"
    Module      = "SGA"
    Feature     = "PostgreSQL Database"
    Description = "Master credentials for Aurora PostgreSQL"
  }
}

resource "aws_secretsmanager_secret_version" "sga_rds_master" {
  secret_id = aws_secretsmanager_secret.sga_rds_master.id

  secret_string = jsonencode({
    username            = "sgaadmin"
    password            = random_password.sga_rds_master.result
    engine              = "postgres"
    host                = aws_rds_cluster.sga.endpoint
    port                = 5432
    dbname              = "sga_inventory"
    dbClusterIdentifier = aws_rds_cluster.sga.cluster_identifier
  })

  # Ensure cluster is created before secret version
  depends_on = [aws_rds_cluster.sga]
}

# =============================================================================
# IAM Role for RDS Proxy
# =============================================================================
# RDS Proxy uses this role to retrieve secrets from Secrets Manager.

resource "aws_iam_role" "sga_rds_proxy" {
  name = "${local.name_prefix}-sga-rds-proxy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "rds.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${local.name_prefix}-sga-rds-proxy-role"
    Module      = "SGA"
    Feature     = "RDS Proxy"
    Description = "IAM role for RDS Proxy to access Secrets Manager"
  }
}

resource "aws_iam_role_policy" "sga_rds_proxy_secrets" {
  name = "${local.name_prefix}-sga-rds-proxy-secrets"
  role = aws_iam_role.sga_rds_proxy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSecretsAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.sga_rds_master.arn
      },
      {
        Sid    = "AllowKMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = aws_kms_key.sga_rds.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_rds_secret_arn" {
  description = "Secrets Manager secret ARN for SGA RDS master credentials"
  value       = aws_secretsmanager_secret.sga_rds_master.arn
}

output "sga_rds_proxy_role_arn" {
  description = "IAM role ARN for SGA RDS Proxy"
  value       = aws_iam_role.sga_rds_proxy.arn
}
