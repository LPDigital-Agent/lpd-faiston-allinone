# =============================================================================
# RDS Proxy for SGA Aurora PostgreSQL
# =============================================================================
# RDS Proxy provides connection pooling for Lambda functions.
#
# Why RDS Proxy is Critical:
# - Lambda creates new DB connections on each cold start
# - Without pooling, connections can exhaust DB capacity
# - Proxy maintains a connection pool to Aurora
# - Lambda connects to Proxy, Proxy reuses connections to Aurora
#
# Architecture:
# Lambda → RDS Proxy → Aurora PostgreSQL
#
# Authentication:
# - Lambda uses IAM auth to connect to Proxy (no password)
# - Proxy uses Secrets Manager credentials to connect to Aurora
#
# Performance:
# - Connection reuse reduces latency
# - 30-second cold start target achievable
# =============================================================================

# =============================================================================
# RDS Proxy
# =============================================================================

resource "aws_db_proxy" "sga" {
  name                   = "${local.name_prefix}-sga-proxy"
  debug_logging          = var.environment != "prod"
  engine_family          = "POSTGRESQL"
  idle_client_timeout    = var.sga_rds_proxy_idle_timeout
  require_tls            = true
  role_arn               = aws_iam_role.sga_rds_proxy.arn
  vpc_security_group_ids = [aws_security_group.sga_rds_proxy.id]
  vpc_subnet_ids         = aws_subnet.sga_database[*].id

  auth {
    auth_scheme               = "SECRETS"
    client_password_auth_type = "POSTGRES_SCRAM_SHA_256"
    description               = "SGA master credentials from Secrets Manager"
    # DISABLED allows both IAM and password auth from clients
    # This enables password auth from Lambda using Secrets Manager credentials
    iam_auth   = "DISABLED"
    secret_arn = aws_secretsmanager_secret.sga_rds_master.arn
  }

  tags = {
    Name        = "${local.name_prefix}-sga-proxy"
    Module      = "SGA"
    Feature     = "RDS Proxy"
    Description = "RDS Proxy for connection pooling to Aurora PostgreSQL"
  }

  depends_on = [
    aws_secretsmanager_secret_version.sga_rds_master,
    aws_iam_role_policy.sga_rds_proxy_secrets
  ]
}

# =============================================================================
# RDS Proxy Default Target Group
# =============================================================================

resource "aws_db_proxy_default_target_group" "sga" {
  db_proxy_name = aws_db_proxy.sga.name

  connection_pool_config {
    connection_borrow_timeout    = 120
    max_connections_percent      = 100
    max_idle_connections_percent = 50
  }
}

# =============================================================================
# RDS Proxy Target (Aurora Cluster)
# =============================================================================

resource "aws_db_proxy_target" "sga" {
  db_proxy_name         = aws_db_proxy.sga.name
  target_group_name     = aws_db_proxy_default_target_group.sga.name
  db_cluster_identifier = aws_rds_cluster.sga.cluster_identifier
}

# =============================================================================
# CloudWatch Alarms for RDS Proxy
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "sga_proxy_connections" {
  alarm_name          = "${local.name_prefix}-sga-proxy-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ClientConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 100
  alarm_description   = "RDS Proxy client connections above 100"

  dimensions = {
    ProxyName = aws_db_proxy.sga.name
  }

  tags = {
    Name        = "${local.name_prefix}-sga-proxy-connections-alarm"
    Module      = "SGA"
    Description = "Alarm for high RDS Proxy connections"
  }
}

resource "aws_cloudwatch_metric_alarm" "sga_proxy_query_latency" {
  alarm_name          = "${local.name_prefix}-sga-proxy-latency-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "QueryDatabaseResponseLatency"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 1000
  alarm_description   = "RDS Proxy query latency above 1 second"

  dimensions = {
    ProxyName = aws_db_proxy.sga.name
  }

  tags = {
    Name        = "${local.name_prefix}-sga-proxy-latency-alarm"
    Module      = "SGA"
    Description = "Alarm for high query latency via RDS Proxy"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_rds_proxy_endpoint" {
  description = "RDS Proxy endpoint for Lambda connections"
  value       = aws_db_proxy.sga.endpoint
}

output "sga_rds_proxy_arn" {
  description = "RDS Proxy ARN"
  value       = aws_db_proxy.sga.arn
}

output "sga_rds_proxy_name" {
  description = "RDS Proxy name"
  value       = aws_db_proxy.sga.name
}
