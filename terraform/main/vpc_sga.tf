# =============================================================================
# VPC for SGA PostgreSQL Database
# =============================================================================
# Dedicated VPC for RDS Aurora PostgreSQL Serverless v2 with Lambda access.
#
# Architecture:
# - 3 Availability Zones for high availability
# - Database subnets (private, no internet access)
# - Lambda subnets (private, VPC endpoints for AWS services)
# - VPC Endpoints for Secrets Manager and RDS
# - No NAT Gateway (cost savings, Lambda uses VPC endpoints)
#
# Security:
# - All subnets are private (no public IP assignment)
# - VPC Flow Logs enabled for audit
# - DNS hostnames enabled for RDS endpoint resolution
# =============================================================================

# =============================================================================
# Data Sources
# =============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

# =============================================================================
# VPC
# =============================================================================

resource "aws_vpc" "sga" {
  cidr_block           = var.sga_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "${local.name_prefix}-sga-vpc"
    Module      = "SGA"
    Feature     = "PostgreSQL Database"
    Description = "VPC for SGA inventory PostgreSQL database"
  }
}

# =============================================================================
# Database Subnets (Private - for RDS Aurora)
# =============================================================================
# These subnets host RDS Aurora PostgreSQL Serverless v2.
# No internet access required - RDS communicates via VPC endpoints.

resource "aws_subnet" "sga_database" {
  count = 3

  vpc_id                  = aws_vpc.sga.id
  cidr_block              = cidrsubnet(var.sga_vpc_cidr, 8, 10 + count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name        = "${local.name_prefix}-sga-db-${data.aws_availability_zones.available.names[count.index]}"
    Type        = "database"
    Module      = "SGA"
    Description = "Database subnet for Aurora PostgreSQL"
  }
}

# =============================================================================
# Lambda Subnets (Private - for VPC-attached Lambda)
# =============================================================================
# These subnets host Lambda functions that need VPC access to RDS.
# Lambda connects to RDS Proxy which is in the database subnets.

resource "aws_subnet" "sga_lambda" {
  count = 3

  vpc_id                  = aws_vpc.sga.id
  cidr_block              = cidrsubnet(var.sga_vpc_cidr, 8, 20 + count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name        = "${local.name_prefix}-sga-lambda-${data.aws_availability_zones.available.names[count.index]}"
    Type        = "lambda"
    Module      = "SGA"
    Description = "Lambda subnet for MCP tools"
  }
}

# =============================================================================
# DB Subnet Group (Required for RDS)
# =============================================================================

resource "aws_db_subnet_group" "sga" {
  name        = "${local.name_prefix}-sga-db-subnet-group"
  description = "Subnet group for SGA Aurora PostgreSQL cluster"
  subnet_ids  = aws_subnet.sga_database[*].id

  tags = {
    Name        = "${local.name_prefix}-sga-db-subnet-group"
    Module      = "SGA"
    Description = "Subnet group spanning 3 AZs for Aurora PostgreSQL"
  }
}

# =============================================================================
# Route Tables
# =============================================================================
# Private route tables with no internet gateway route.
# Traffic to AWS services goes through VPC endpoints.

resource "aws_route_table" "sga_database" {
  vpc_id = aws_vpc.sga.id

  tags = {
    Name        = "${local.name_prefix}-sga-db-rt"
    Type        = "database"
    Module      = "SGA"
    Description = "Route table for database subnets"
  }
}

resource "aws_route_table" "sga_lambda" {
  vpc_id = aws_vpc.sga.id

  tags = {
    Name        = "${local.name_prefix}-sga-lambda-rt"
    Type        = "lambda"
    Module      = "SGA"
    Description = "Route table for Lambda subnets"
  }
}

# =============================================================================
# Route Table Associations
# =============================================================================

resource "aws_route_table_association" "sga_database" {
  count = 3

  subnet_id      = aws_subnet.sga_database[count.index].id
  route_table_id = aws_route_table.sga_database.id
}

resource "aws_route_table_association" "sga_lambda" {
  count = 3

  subnet_id      = aws_subnet.sga_lambda[count.index].id
  route_table_id = aws_route_table.sga_lambda.id
}

# =============================================================================
# VPC Endpoints
# =============================================================================
# Interface endpoints for AWS services (Lambda needs these for:
# - Secrets Manager: RDS Proxy credential retrieval
# - RDS: Database connections
# - CloudWatch Logs: Lambda logging

# Secrets Manager Endpoint (required for RDS Proxy IAM auth)
resource "aws_vpc_endpoint" "sga_secretsmanager" {
  vpc_id              = aws_vpc.sga.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  subnet_ids         = aws_subnet.sga_lambda[*].id
  security_group_ids = [aws_security_group.sga_vpc_endpoints.id]

  tags = {
    Name        = "${local.name_prefix}-sga-secretsmanager-endpoint"
    Module      = "SGA"
    Description = "Secrets Manager endpoint for RDS Proxy credentials"
  }
}

# RDS Endpoint (for RDS API calls)
resource "aws_vpc_endpoint" "sga_rds" {
  vpc_id              = aws_vpc.sga.id
  service_name        = "com.amazonaws.${var.aws_region}.rds"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  subnet_ids         = aws_subnet.sga_lambda[*].id
  security_group_ids = [aws_security_group.sga_vpc_endpoints.id]

  tags = {
    Name        = "${local.name_prefix}-sga-rds-endpoint"
    Module      = "SGA"
    Description = "RDS endpoint for database API calls"
  }
}

# CloudWatch Logs Endpoint (for Lambda logging)
resource "aws_vpc_endpoint" "sga_logs" {
  vpc_id              = aws_vpc.sga.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  subnet_ids         = aws_subnet.sga_lambda[*].id
  security_group_ids = [aws_security_group.sga_vpc_endpoints.id]

  tags = {
    Name        = "${local.name_prefix}-sga-logs-endpoint"
    Module      = "SGA"
    Description = "CloudWatch Logs endpoint for Lambda logging"
  }
}

# STS Endpoint (for IAM authentication)
resource "aws_vpc_endpoint" "sga_sts" {
  vpc_id              = aws_vpc.sga.id
  service_name        = "com.amazonaws.${var.aws_region}.sts"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  subnet_ids         = aws_subnet.sga_lambda[*].id
  security_group_ids = [aws_security_group.sga_vpc_endpoints.id]

  tags = {
    Name        = "${local.name_prefix}-sga-sts-endpoint"
    Module      = "SGA"
    Description = "STS endpoint for IAM authentication"
  }
}

# S3 Gateway Endpoint (for schema file downloads)
# NOTE: S3 uses Gateway type (free), not Interface type
# Gateway endpoints route through route table, not ENIs
resource "aws_vpc_endpoint" "sga_s3" {
  vpc_id            = aws_vpc.sga.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"

  # Associate with Lambda route table so Lambda can reach S3
  route_table_ids = [aws_route_table.sga_lambda.id]

  tags = {
    Name        = "${local.name_prefix}-sga-s3-endpoint"
    Module      = "SGA"
    Description = "S3 gateway endpoint for schema file downloads"
  }
}

# =============================================================================
# VPC Flow Logs (Audit)
# =============================================================================

resource "aws_flow_log" "sga" {
  vpc_id                   = aws_vpc.sga.id
  traffic_type             = "ALL"
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.sga_vpc_flow_logs.arn
  iam_role_arn             = aws_iam_role.sga_vpc_flow_logs.arn
  max_aggregation_interval = 60

  tags = {
    Name        = "${local.name_prefix}-sga-vpc-flow-logs"
    Module      = "SGA"
    Description = "VPC flow logs for audit and troubleshooting"
  }
}

resource "aws_cloudwatch_log_group" "sga_vpc_flow_logs" {
  name              = "/aws/vpc/${local.name_prefix}-sga-vpc/flow-logs"
  retention_in_days = 30

  tags = {
    Name        = "${local.name_prefix}-sga-vpc-flow-logs"
    Module      = "SGA"
    Description = "Log group for VPC flow logs"
  }
}

resource "aws_iam_role" "sga_vpc_flow_logs" {
  name = "${local.name_prefix}-sga-vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${local.name_prefix}-sga-vpc-flow-logs-role"
    Module      = "SGA"
    Description = "IAM role for VPC flow logs"
  }
}

resource "aws_iam_role_policy" "sga_vpc_flow_logs" {
  name = "${local.name_prefix}-sga-vpc-flow-logs-policy"
  role = aws_iam_role.sga_vpc_flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ]
      Resource = "*"
    }]
  })
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_vpc_id" {
  description = "VPC ID for SGA PostgreSQL"
  value       = aws_vpc.sga.id
}

output "sga_database_subnet_ids" {
  description = "Database subnet IDs for Aurora PostgreSQL"
  value       = aws_subnet.sga_database[*].id
}

output "sga_lambda_subnet_ids" {
  description = "Lambda subnet IDs for MCP tools"
  value       = aws_subnet.sga_lambda[*].id
}

output "sga_db_subnet_group_name" {
  description = "DB subnet group name for Aurora cluster"
  value       = aws_db_subnet_group.sga.name
}
