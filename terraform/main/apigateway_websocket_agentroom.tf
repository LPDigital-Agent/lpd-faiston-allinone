# =============================================================================
# API Gateway WebSocket for Agent Room Real-Time Events
# =============================================================================
# Provides real-time event streaming to Agent Room UI via WebSocket.
#
# Architecture:
# DynamoDB Streams → EventBridge Pipe → Lambda → WebSocket → Frontend
#
# Key Features:
# - Managed WebSocket connections (API Gateway handles lifecycle)
# - Connection tracking in DynamoDB with TTL auto-cleanup
# - <100ms latency for real-time agent activity updates
#
# Routes:
# - $connect    : Store connection in DynamoDB
# - $disconnect : Remove connection from DynamoDB
# - $default    : Not used (push-only, no client messages)
# =============================================================================

# =============================================================================
# WebSocket API Gateway
# =============================================================================

resource "aws_apigatewayv2_api" "agent_room_websocket" {
  name                       = "${local.name_prefix}-agentroom-ws"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"

  tags = {
    Name        = "${local.name_prefix}-agentroom-ws"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "WebSocket API for real-time agent activity streaming"
  }
}

# =============================================================================
# Connection Tracking DynamoDB Table
# =============================================================================
# Stores active WebSocket connections for broadcast targeting.
# TTL ensures stale connections are automatically cleaned up.

resource "aws_dynamodb_table" "websocket_connections" {
  name         = "${local.name_prefix}-agentroom-connections"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "connectionId"

  attribute {
    name = "connectionId"
    type = "S"
  }

  # TTL for auto-cleanup of stale connections (24 hours)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${local.name_prefix}-agentroom-connections"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "Tracks active WebSocket connections for event broadcast"
    Retention   = "TTL-24h"
  }
}

# =============================================================================
# IAM Role for WebSocket Lambda Functions
# =============================================================================

resource "aws_iam_role" "websocket_lambda" {
  name = "${local.name_prefix}-agentroom-ws-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${local.name_prefix}-agentroom-ws-lambda-role"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "IAM role for WebSocket connect/disconnect Lambdas"
  }
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "websocket_lambda_basic" {
  role       = aws_iam_role.websocket_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# DynamoDB access for connection tracking
resource "aws_iam_role_policy" "websocket_lambda_dynamodb" {
  name = "${local.name_prefix}-agentroom-ws-dynamodb"
  role = aws_iam_role.websocket_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowConnectionTracking"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.websocket_connections.arn
      }
    ]
  })
}

# =============================================================================
# Lambda: $connect Handler
# =============================================================================
# Stores new connections in DynamoDB when clients connect.

data "archive_file" "websocket_connect" {
  type        = "zip"
  output_path = "${path.module}/lambda_packages/agentroom-ws-connect.zip"

  source {
    content = <<-EOF
"""WebSocket $connect handler - stores connection in DynamoDB."""
import os
import boto3
import time
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

def handler(event, context):
    connection_id = event['requestContext']['connectionId']

    # Extract user_id from query string (optional)
    query_params = event.get('queryStringParameters') or {}
    user_id = query_params.get('user_id', 'anonymous')

    # Store connection with 24-hour TTL
    table.put_item(Item={
        'connectionId': connection_id,
        'userId': user_id,
        'connectedAt': datetime.utcnow().isoformat(),
        'ttl': int(time.time()) + 86400  # 24 hours
    })

    print(f"[AgentRoom WS] Connected: {connection_id} (user: {user_id})")

    return {'statusCode': 200, 'body': 'Connected'}
EOF
    filename = "index.py"
  }
}

resource "aws_lambda_function" "websocket_connect" {
  function_name    = "${local.name_prefix}-agentroom-ws-connect"
  role             = aws_iam_role.websocket_lambda.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "index.handler"
  filename         = data.archive_file.websocket_connect.output_path
  source_code_hash = data.archive_file.websocket_connect.output_base64sha256
  timeout          = 10

  environment {
    variables = {
      CONNECTIONS_TABLE = aws_dynamodb_table.websocket_connections.name
    }
  }

  tags = {
    Name        = "${local.name_prefix}-agentroom-ws-connect"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "Handles WebSocket $connect route"
  }
}

# Permission for API Gateway to invoke connect Lambda
resource "aws_lambda_permission" "websocket_connect" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.websocket_connect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.agent_room_websocket.execution_arn}/*/*"
}

# =============================================================================
# Lambda: $disconnect Handler
# =============================================================================
# Removes connections from DynamoDB when clients disconnect.

data "archive_file" "websocket_disconnect" {
  type        = "zip"
  output_path = "${path.module}/lambda_packages/agentroom-ws-disconnect.zip"

  source {
    content = <<-EOF
"""WebSocket $disconnect handler - removes connection from DynamoDB."""
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

def handler(event, context):
    connection_id = event['requestContext']['connectionId']

    # Remove connection from tracking table
    table.delete_item(Key={'connectionId': connection_id})

    print(f"[AgentRoom WS] Disconnected: {connection_id}")

    return {'statusCode': 200, 'body': 'Disconnected'}
EOF
    filename = "index.py"
  }
}

resource "aws_lambda_function" "websocket_disconnect" {
  function_name    = "${local.name_prefix}-agentroom-ws-disconnect"
  role             = aws_iam_role.websocket_lambda.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "index.handler"
  filename         = data.archive_file.websocket_disconnect.output_path
  source_code_hash = data.archive_file.websocket_disconnect.output_base64sha256
  timeout          = 10

  environment {
    variables = {
      CONNECTIONS_TABLE = aws_dynamodb_table.websocket_connections.name
    }
  }

  tags = {
    Name        = "${local.name_prefix}-agentroom-ws-disconnect"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "Handles WebSocket $disconnect route"
  }
}

# Permission for API Gateway to invoke disconnect Lambda
resource "aws_lambda_permission" "websocket_disconnect" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.websocket_disconnect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.agent_room_websocket.execution_arn}/*/*"
}

# =============================================================================
# API Gateway Integrations
# =============================================================================

resource "aws_apigatewayv2_integration" "connect" {
  api_id             = aws_apigatewayv2_api.agent_room_websocket.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.websocket_connect.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_integration" "disconnect" {
  api_id             = aws_apigatewayv2_api.agent_room_websocket.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.websocket_disconnect.invoke_arn
  integration_method = "POST"
}

# =============================================================================
# API Gateway Routes
# =============================================================================

resource "aws_apigatewayv2_route" "connect" {
  api_id    = aws_apigatewayv2_api.agent_room_websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.connect.id}"
}

resource "aws_apigatewayv2_route" "disconnect" {
  api_id    = aws_apigatewayv2_api.agent_room_websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.disconnect.id}"
}

# =============================================================================
# API Gateway Stage (Production)
# =============================================================================

resource "aws_apigatewayv2_stage" "production" {
  api_id      = aws_apigatewayv2_api.agent_room_websocket.id
  name        = "production"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 500
    throttling_rate_limit  = 1000
  }

  tags = {
    Name        = "${local.name_prefix}-agentroom-ws-prod"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Environment = var.environment
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "agentroom_websocket_url" {
  description = "WebSocket URL for Agent Room real-time events"
  value       = aws_apigatewayv2_stage.production.invoke_url
}

output "agentroom_websocket_api_id" {
  description = "API Gateway WebSocket API ID"
  value       = aws_apigatewayv2_api.agent_room_websocket.id
}

output "agentroom_websocket_endpoint" {
  description = "WebSocket endpoint for API Gateway Management API"
  value       = replace(aws_apigatewayv2_stage.production.invoke_url, "wss://", "https://")
}

output "agentroom_connections_table_name" {
  description = "DynamoDB table name for WebSocket connections"
  value       = aws_dynamodb_table.websocket_connections.name
}
