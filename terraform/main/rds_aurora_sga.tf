# =============================================================================
# RDS Aurora PostgreSQL Serverless v2 for SGA Inventory
# =============================================================================
# Aurora PostgreSQL Serverless v2 cluster for SGA inventory management.
#
# Architecture:
# - Serverless v2 with automatic scaling (0.5-8 ACU)
# - Multi-AZ deployment (3 AZs)
# - Point-in-Time Recovery (PITR) enabled
# - Performance Insights for monitoring
#
# Scaling:
# - Min ACU: 0.5 (scales to zero when idle in dev)
# - Max ACU: 8.0 (handles analytics workloads)
# - Auto-scaling based on CPU, memory, and connections
#
# Security:
# - KMS encryption at rest
# - TLS encryption in transit
# - IAM authentication for Lambda
# - No public accessibility
# =============================================================================

# =============================================================================
# Aurora Cluster
# =============================================================================

resource "aws_rds_cluster" "sga" {
  cluster_identifier = "${local.name_prefix}-sga-postgres"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = var.sga_aurora_engine_version
  database_name      = "sga_inventory"
  master_username    = "sgaadmin"
  master_password    = random_password.sga_rds_master.result

  # Network Configuration
  db_subnet_group_name   = aws_db_subnet_group.sga.name
  vpc_security_group_ids = [aws_security_group.sga_aurora.id]
  port                   = 5432

  # Serverless v2 Configuration
  serverlessv2_scaling_configuration {
    min_capacity = var.sga_aurora_min_capacity
    max_capacity = var.sga_aurora_max_capacity
  }

  # Security
  storage_encrypted                   = true
  kms_key_id                          = aws_kms_key.sga_rds.arn
  iam_database_authentication_enabled = true

  # Backup Configuration
  backup_retention_period   = 7
  preferred_backup_window   = "03:00-04:00"
  copy_tags_to_snapshot     = true
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.name_prefix}-sga-final-snapshot" : null

  # Maintenance
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  apply_immediately            = var.environment != "prod"

  # Deletion Protection
  deletion_protection = var.environment == "prod"

  # Logging
  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name        = "${local.name_prefix}-sga-postgres"
    Module      = "SGA"
    Feature     = "PostgreSQL Database"
    Description = "Aurora PostgreSQL Serverless v2 for inventory management"
  }
}

# =============================================================================
# Aurora Cluster Instance (Serverless v2)
# =============================================================================
# Serverless v2 requires at least one instance with db.serverless class.

resource "aws_rds_cluster_instance" "sga" {
  identifier         = "${local.name_prefix}-sga-postgres-instance-1"
  cluster_identifier = aws_rds_cluster.sga.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.sga.engine
  engine_version     = aws_rds_cluster.sga.engine_version

  # Monitoring
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = aws_kms_key.sga_rds.arn
  performance_insights_retention_period = 7
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.sga_rds_monitoring.arn

  # No public access
  publicly_accessible = false

  # Apply immediately in non-prod
  apply_immediately = var.environment != "prod"

  tags = {
    Name        = "${local.name_prefix}-sga-postgres-instance-1"
    Module      = "SGA"
    Feature     = "PostgreSQL Database"
    Description = "Aurora Serverless v2 writer instance"
  }
}

# =============================================================================
# Enhanced Monitoring IAM Role
# =============================================================================

resource "aws_iam_role" "sga_rds_monitoring" {
  name = "${local.name_prefix}-sga-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${local.name_prefix}-sga-rds-monitoring-role"
    Module      = "SGA"
    Feature     = "RDS Monitoring"
    Description = "IAM role for RDS Enhanced Monitoring"
  }
}

resource "aws_iam_role_policy_attachment" "sga_rds_monitoring" {
  role       = aws_iam_role.sga_rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# =============================================================================
# CloudWatch Alarms
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "sga_aurora_cpu" {
  alarm_name          = "${local.name_prefix}-sga-aurora-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Aurora CPU utilization is above 80% for 15 minutes"

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.sga.cluster_identifier
  }

  tags = {
    Name        = "${local.name_prefix}-sga-aurora-cpu-alarm"
    Module      = "SGA"
    Description = "Alarm for high CPU utilization"
  }
}

resource "aws_cloudwatch_metric_alarm" "sga_aurora_connections" {
  alarm_name          = "${local.name_prefix}-sga-aurora-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Aurora database connections above 80"

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.sga.cluster_identifier
  }

  tags = {
    Name        = "${local.name_prefix}-sga-aurora-connections-alarm"
    Module      = "SGA"
    Description = "Alarm for high connection count"
  }
}

resource "aws_cloudwatch_metric_alarm" "sga_aurora_acu" {
  alarm_name          = "${local.name_prefix}-sga-aurora-acu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ServerlessDatabaseCapacity"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.sga_aurora_max_capacity * 0.8
  alarm_description   = "Aurora ACU capacity is above 80% of max"

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.sga.cluster_identifier
  }

  tags = {
    Name        = "${local.name_prefix}-sga-aurora-acu-alarm"
    Module      = "SGA"
    Description = "Alarm for high ACU capacity"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_aurora_cluster_endpoint" {
  description = "Aurora cluster writer endpoint"
  value       = aws_rds_cluster.sga.endpoint
}

output "sga_aurora_cluster_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = aws_rds_cluster.sga.reader_endpoint
}

output "sga_aurora_cluster_id" {
  description = "Aurora cluster identifier"
  value       = aws_rds_cluster.sga.cluster_identifier
}

output "sga_aurora_cluster_arn" {
  description = "Aurora cluster ARN"
  value       = aws_rds_cluster.sga.arn
}

output "sga_aurora_database_name" {
  description = "Aurora database name"
  value       = aws_rds_cluster.sga.database_name
}

output "sga_aurora_port" {
  description = "Aurora cluster port"
  value       = aws_rds_cluster.sga.port
}
