# =============================================================================
# Security Groups for SGA PostgreSQL Infrastructure
# =============================================================================
# Security group chain for Lambda → RDS Proxy → Aurora PostgreSQL.
#
# Architecture:
# ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
# │  Lambda SG      │────▶│  RDS Proxy SG   │────▶│  Aurora SG      │
# │  (MCP Tools)    │     │  (Port 5432)    │     │  (Port 5432)    │
# └─────────────────┘     └─────────────────┘     └─────────────────┘
#
# Security Principles:
# - Least privilege: Each SG only allows required ports
# - Source-based rules: Only specific SGs can access each other
# - No 0.0.0.0/0: All traffic is internal to VPC
# - VPC Endpoints: Separate SG for AWS service endpoints
# =============================================================================

# =============================================================================
# Lambda Security Group
# =============================================================================
# Security group for Lambda functions that invoke PostgreSQL tools via MCP.
# Allows outbound traffic to:
# - RDS Proxy (port 5432)
# - VPC Endpoints (HTTPS for AWS services)

resource "aws_security_group" "sga_lambda" {
  name        = "${local.name_prefix}-sga-lambda-sg"
  description = "Security group for SGA Lambda MCP tools"
  vpc_id      = aws_vpc.sga.id

  tags = {
    Name        = "${local.name_prefix}-sga-lambda-sg"
    Module      = "SGA"
    Feature     = "MCP Tools"
    Description = "Security group for Lambda functions accessing PostgreSQL"
  }
}

# Egress: Lambda → RDS Proxy (PostgreSQL)
resource "aws_vpc_security_group_egress_rule" "sga_lambda_to_proxy" {
  security_group_id            = aws_security_group.sga_lambda.id
  description                  = "Allow Lambda to connect to RDS Proxy"
  referenced_security_group_id = aws_security_group.sga_rds_proxy.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

# Egress: Lambda → VPC Endpoints (HTTPS)
resource "aws_vpc_security_group_egress_rule" "sga_lambda_to_endpoints" {
  security_group_id            = aws_security_group.sga_lambda.id
  description                  = "Allow Lambda to connect to VPC endpoints"
  referenced_security_group_id = aws_security_group.sga_vpc_endpoints.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

# =============================================================================
# RDS Proxy Security Group
# =============================================================================
# Security group for RDS Proxy (connection pooling layer).
# Allows inbound from Lambda, outbound to Aurora.

resource "aws_security_group" "sga_rds_proxy" {
  name        = "${local.name_prefix}-sga-rds-proxy-sg"
  description = "Security group for SGA RDS Proxy"
  vpc_id      = aws_vpc.sga.id

  tags = {
    Name        = "${local.name_prefix}-sga-rds-proxy-sg"
    Module      = "SGA"
    Feature     = "RDS Proxy"
    Description = "Security group for RDS Proxy connection pooling"
  }
}

# Ingress: Lambda → RDS Proxy (PostgreSQL)
resource "aws_vpc_security_group_ingress_rule" "sga_proxy_from_lambda" {
  security_group_id            = aws_security_group.sga_rds_proxy.id
  description                  = "Allow connections from Lambda functions"
  referenced_security_group_id = aws_security_group.sga_lambda.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

# Egress: RDS Proxy → Aurora (PostgreSQL)
resource "aws_vpc_security_group_egress_rule" "sga_proxy_to_aurora" {
  security_group_id            = aws_security_group.sga_rds_proxy.id
  description                  = "Allow RDS Proxy to connect to Aurora cluster"
  referenced_security_group_id = aws_security_group.sga_aurora.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

# Egress: RDS Proxy → VPC Endpoints (for Secrets Manager)
resource "aws_vpc_security_group_egress_rule" "sga_proxy_to_endpoints" {
  security_group_id            = aws_security_group.sga_rds_proxy.id
  description                  = "Allow RDS Proxy to access Secrets Manager"
  referenced_security_group_id = aws_security_group.sga_vpc_endpoints.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

# =============================================================================
# Aurora PostgreSQL Security Group
# =============================================================================
# Security group for Aurora PostgreSQL cluster.
# Only allows inbound from RDS Proxy.

resource "aws_security_group" "sga_aurora" {
  name        = "${local.name_prefix}-sga-aurora-sg"
  description = "Security group for SGA Aurora PostgreSQL cluster"
  vpc_id      = aws_vpc.sga.id

  tags = {
    Name        = "${local.name_prefix}-sga-aurora-sg"
    Module      = "SGA"
    Feature     = "Aurora PostgreSQL"
    Description = "Security group for Aurora PostgreSQL Serverless v2"
  }
}

# Ingress: RDS Proxy → Aurora (PostgreSQL)
resource "aws_vpc_security_group_ingress_rule" "sga_aurora_from_proxy" {
  security_group_id            = aws_security_group.sga_aurora.id
  description                  = "Allow connections from RDS Proxy"
  referenced_security_group_id = aws_security_group.sga_rds_proxy.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

# =============================================================================
# VPC Endpoints Security Group
# =============================================================================
# Security group for VPC Interface Endpoints.
# Allows HTTPS inbound from Lambda and RDS Proxy.

resource "aws_security_group" "sga_vpc_endpoints" {
  name        = "${local.name_prefix}-sga-vpc-endpoints-sg"
  description = "Security group for SGA VPC endpoints"
  vpc_id      = aws_vpc.sga.id

  tags = {
    Name        = "${local.name_prefix}-sga-vpc-endpoints-sg"
    Module      = "SGA"
    Feature     = "VPC Endpoints"
    Description = "Security group for AWS service VPC endpoints"
  }
}

# Ingress: Lambda → VPC Endpoints (HTTPS)
resource "aws_vpc_security_group_ingress_rule" "sga_endpoints_from_lambda" {
  security_group_id            = aws_security_group.sga_vpc_endpoints.id
  description                  = "Allow HTTPS from Lambda functions"
  referenced_security_group_id = aws_security_group.sga_lambda.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

# Ingress: RDS Proxy → VPC Endpoints (HTTPS for Secrets Manager)
resource "aws_vpc_security_group_ingress_rule" "sga_endpoints_from_proxy" {
  security_group_id            = aws_security_group.sga_vpc_endpoints.id
  description                  = "Allow HTTPS from RDS Proxy"
  referenced_security_group_id = aws_security_group.sga_rds_proxy.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

# =============================================================================
# Outputs
# =============================================================================

output "sga_lambda_security_group_id" {
  description = "Security group ID for SGA Lambda functions"
  value       = aws_security_group.sga_lambda.id
}

output "sga_rds_proxy_security_group_id" {
  description = "Security group ID for SGA RDS Proxy"
  value       = aws_security_group.sga_rds_proxy.id
}

output "sga_aurora_security_group_id" {
  description = "Security group ID for SGA Aurora PostgreSQL"
  value       = aws_security_group.sga_aurora.id
}

output "sga_vpc_endpoints_security_group_id" {
  description = "Security group ID for SGA VPC endpoints"
  value       = aws_security_group.sga_vpc_endpoints.id
}
