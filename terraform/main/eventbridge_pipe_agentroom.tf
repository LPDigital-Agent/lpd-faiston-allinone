# =============================================================================
# EventBridge Pipe for Agent Room Real-Time Events
# =============================================================================
# Streams DynamoDB audit events to WebSocket clients in real-time.
#
# Pipeline:
# DynamoDB Streams → Filter → Enrich → Broadcast → WebSocket Clients
#
# Key Features:
# - Filters for AGENT_* events only (reduces noise)
# - Enriches with friendly agent names and classifications
# - Broadcasts to all connected WebSocket clients
# - <100ms end-to-end latency target
#
# References:
# - DynamoDB Streams: dynamodb_sga_audit.tf
# - WebSocket API: apigateway_websocket_agentroom.tf
# =============================================================================

# =============================================================================
# IAM Role for EventBridge Pipes
# =============================================================================

resource "aws_iam_role" "eventbridge_pipe" {
  name = "${local.name_prefix}-agentroom-pipe-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "pipes.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${local.name_prefix}-agentroom-pipe-role"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "IAM role for EventBridge Pipe"
  }
}

# Allow pipe to read from DynamoDB Streams
resource "aws_iam_role_policy" "eventbridge_pipe_source" {
  name = "${local.name_prefix}-agentroom-pipe-source"
  role = aws_iam_role.eventbridge_pipe.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowDynamoDBStreams"
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeStream",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams"
        ]
        Resource = aws_dynamodb_table.sga_audit_log.stream_arn
      }
    ]
  })
}

# Allow pipe to invoke enrichment and target Lambdas
resource "aws_iam_role_policy" "eventbridge_pipe_lambda" {
  name = "${local.name_prefix}-agentroom-pipe-lambda"
  role = aws_iam_role.eventbridge_pipe.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaInvoke"
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.event_enricher.arn,
          aws_lambda_function.websocket_broadcast.arn
        ]
      }
    ]
  })
}

# =============================================================================
# IAM Role for Broadcast Lambda
# =============================================================================
# Separate role with API Gateway Management API permissions

resource "aws_iam_role" "websocket_broadcast" {
  name = "${local.name_prefix}-agentroom-broadcast-role"

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
    Name        = "${local.name_prefix}-agentroom-broadcast-role"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "IAM role for WebSocket broadcast Lambda"
  }
}

resource "aws_iam_role_policy_attachment" "websocket_broadcast_basic" {
  role       = aws_iam_role.websocket_broadcast.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# DynamoDB access for reading connections
resource "aws_iam_role_policy" "websocket_broadcast_dynamodb" {
  name = "${local.name_prefix}-agentroom-broadcast-dynamodb"
  role = aws_iam_role.websocket_broadcast.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowScanConnections"
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.websocket_connections.arn
      }
    ]
  })
}

# API Gateway Management API for posting to connections
resource "aws_iam_role_policy" "websocket_broadcast_apigw" {
  name = "${local.name_prefix}-agentroom-broadcast-apigw"
  role = aws_iam_role.websocket_broadcast.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPostToConnection"
        Effect = "Allow"
        Action = [
          "execute-api:ManageConnections"
        ]
        Resource = "${aws_apigatewayv2_api.agent_room_websocket.execution_arn}/production/POST/@connections/*"
      }
    ]
  })
}

# =============================================================================
# Lambda: Event Enricher
# =============================================================================
# Transforms DynamoDB Stream records into frontend-friendly format.
# Adds: friendly names, event type classification, unmarshal DynamoDB types

data "archive_file" "event_enricher" {
  type        = "zip"
  output_path = "${path.module}/lambda_packages/agentroom-event-enricher.zip"

  source {
    content = <<-EOF
"""EventBridge Pipe enrichment - transforms DynamoDB records for frontend."""

AGENT_NAMES = {
    'nexo_import': 'NEXO',
    'intake': 'Leitor de Notas',
    'import': 'Importador',
    'estoque_control': 'Controlador',
    'stock_control': 'Controlador',
    'compliance': 'Validador',
    'reconciliacao': 'Reconciliador',
    'expedition': 'Despachante',
    'carrier': 'Logistica',
    'reverse': 'Reversa',
    'schema_evolution': 'Arquiteto',
    'learning': 'Memoria',
    'observation': 'Observador',
    'equipment_research': 'Pesquisador',
    'validation': 'Validador',
    'comunicacao': 'Comunicador',
}

def handler(events, context):
    """Enrich DynamoDB stream events for frontend consumption."""
    enriched = []

    for record in events:
        # Handle both direct records and nested event structure
        ddb = record.get('dynamodb', record)
        new_image = ddb.get('NewImage', {})

        if not new_image:
            continue

        # Extract fields from DynamoDB format
        agent_id = get_string(new_image, 'actor_id', '')
        details = unmarshal_dynamodb(new_image.get('details', {}))
        action = get_string(new_image, 'action', 'trabalhando')

        event = {
            'id': get_string(new_image, 'SK', ''),
            'timestamp': get_string(new_image, 'timestamp', ''),
            'type': classify_event_type(action, details),
            'agentId': agent_id,
            'agentName': AGENT_NAMES.get(agent_id, agent_id or 'Sistema'),
            'action': action,
            'message': details.get('message', ''),
            'sessionId': get_string(new_image, 'GSI4PK', '').replace('SESSION#', '') or None,
            'targetAgent': details.get('target_agent'),
            'targetAgentName': AGENT_NAMES.get(details.get('target_agent'), details.get('target_agent')),
            'details': details,
        }

        # Add HIL fields if present
        if details.get('hil_task_id'):
            event['hilTaskId'] = details['hil_task_id']
            event['hilStatus'] = 'pending'
            event['hilQuestion'] = details.get('question', '')
            event['hilOptions'] = details.get('options', [])

        enriched.append(event)

    print(f"[Enricher] Processed {len(enriched)} events")
    return enriched


def get_string(obj, key, default=''):
    """Extract string value from DynamoDB format."""
    val = obj.get(key, {})
    if isinstance(val, dict):
        return val.get('S', default)
    return val if val else default


def classify_event_type(action, details):
    """Classify event into type categories."""
    if details.get('target_agent'):
        return 'a2a_delegation'
    if action in ('erro', 'error'):
        return 'error'
    if 'hil' in action.lower() or details.get('hil_task_id'):
        return 'hil_decision'
    if action in ('started', 'iniciado'):
        return 'session_start'
    if action in ('completed', 'concluido'):
        return 'session_end'
    return 'agent_activity'


def unmarshal_dynamodb(obj):
    """Convert DynamoDB format to plain Python dict."""
    if not isinstance(obj, dict):
        return obj

    if 'S' in obj:
        return obj['S']
    if 'N' in obj:
        try:
            n = obj['N']
            return int(n) if '.' not in n else float(n)
        except:
            return obj['N']
    if 'BOOL' in obj:
        return obj['BOOL']
    if 'NULL' in obj:
        return None
    if 'M' in obj:
        return {k: unmarshal_dynamodb(v) for k, v in obj['M'].items()}
    if 'L' in obj:
        return [unmarshal_dynamodb(v) for v in obj['L']]
    if 'SS' in obj:
        return list(obj['SS'])
    if 'NS' in obj:
        return [float(n) if '.' in n else int(n) for n in obj['NS']]

    # If no type markers, it's already unmarshalled or nested
    return {k: unmarshal_dynamodb(v) for k, v in obj.items()} if obj else obj
EOF
    filename = "index.py"
  }
}

resource "aws_lambda_function" "event_enricher" {
  function_name    = "${local.name_prefix}-agentroom-event-enricher"
  role             = aws_iam_role.websocket_lambda.arn # Reuse basic Lambda role
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "index.handler"
  filename         = data.archive_file.event_enricher.output_path
  source_code_hash = data.archive_file.event_enricher.output_base64sha256
  timeout          = 15
  memory_size      = 256

  tags = {
    Name        = "${local.name_prefix}-agentroom-event-enricher"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "Enriches DynamoDB stream events for WebSocket broadcast"
  }
}

# =============================================================================
# Lambda: WebSocket Broadcast
# =============================================================================
# Pushes enriched events to all connected WebSocket clients.

data "archive_file" "websocket_broadcast" {
  type        = "zip"
  output_path = "${path.module}/lambda_packages/agentroom-ws-broadcast.zip"

  source {
    content = <<-EOF
"""WebSocket broadcast - pushes events to all connected clients."""
import os
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

# API Gateway Management API
endpoint = os.environ['WEBSOCKET_ENDPOINT']
apigw = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)

def handler(events, context):
    """Broadcast enriched events to all WebSocket connections."""
    if not events:
        return {'statusCode': 200, 'body': 'No events to broadcast'}

    # Get all active connections
    response = table.scan(
        ProjectionExpression='connectionId'
    )
    connections = response.get('Items', [])

    # Handle pagination for large connection pools
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ProjectionExpression='connectionId',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        connections.extend(response.get('Items', []))

    if not connections:
        print("[Broadcast] No active connections")
        return {'statusCode': 200, 'body': 'No connections'}

    # Prepare message
    message = json.dumps({
        'type': 'agent_events',
        'events': events
    })
    message_bytes = message.encode('utf-8')

    # Broadcast to all connections
    stale_connections = []
    success_count = 0

    for conn in connections:
        connection_id = conn['connectionId']
        try:
            apigw.post_to_connection(
                ConnectionId=connection_id,
                Data=message_bytes
            )
            success_count += 1
        except apigw.exceptions.GoneException:
            # Connection is stale, mark for deletion
            stale_connections.append(connection_id)
        except Exception as e:
            print(f"[Broadcast] Error sending to {connection_id}: {e}")

    # Cleanup stale connections
    for connection_id in stale_connections:
        try:
            table.delete_item(Key={'connectionId': connection_id})
        except Exception as e:
            print(f"[Broadcast] Error deleting stale connection {connection_id}: {e}")

    print(f"[Broadcast] Sent {len(events)} events to {success_count}/{len(connections)} connections, cleaned {len(stale_connections)} stale")

    return {
        'statusCode': 200,
        'body': f'Broadcast to {success_count} connections'
    }
EOF
    filename = "index.py"
  }
}

resource "aws_lambda_function" "websocket_broadcast" {
  function_name    = "${local.name_prefix}-agentroom-ws-broadcast"
  role             = aws_iam_role.websocket_broadcast.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "index.handler"
  filename         = data.archive_file.websocket_broadcast.output_path
  source_code_hash = data.archive_file.websocket_broadcast.output_base64sha256
  timeout          = 60 # Allow time for broadcasting to many connections
  memory_size      = 256

  environment {
    variables = {
      CONNECTIONS_TABLE  = aws_dynamodb_table.websocket_connections.name
      WEBSOCKET_ENDPOINT = replace(aws_apigatewayv2_stage.production.invoke_url, "wss://", "https://")
    }
  }

  tags = {
    Name        = "${local.name_prefix}-agentroom-ws-broadcast"
    Module      = "SGA"
    Feature     = "Agent Room Real-Time"
    Description = "Broadcasts events to all WebSocket connections"
  }
}

# =============================================================================
# EventBridge Pipe
# =============================================================================
# Connects DynamoDB Streams to Lambda via enrichment pipeline.

resource "aws_pipes_pipe" "agent_room_events" {
  name     = "${local.name_prefix}-agentroom-events"
  role_arn = aws_iam_role.eventbridge_pipe.arn

  source = aws_dynamodb_table.sga_audit_log.stream_arn

  source_parameters {
    dynamodb_stream_parameters {
      starting_position             = "LATEST"
      batch_size                    = 10
      maximum_batching_window_in_seconds = 1 # Low latency batch
    }

    filter_criteria {
      filter {
        # Only process AGENT activity events (not USER, SYSTEM, etc.)
        pattern = jsonencode({
          eventName = ["INSERT"] # Audit log is append-only
          dynamodb = {
            NewImage = {
              actor_type = {
                S = ["AGENT"]
              }
            }
          }
        })
      }
    }
  }

  # Enrichment step: Transform DynamoDB format to frontend format
  enrichment = aws_lambda_function.event_enricher.arn

  # Target: Broadcast Lambda
  target = aws_lambda_function.websocket_broadcast.arn

  target_parameters {
    input_template = jsonencode({})
  }

  tags = {
    Name    = "${local.name_prefix}-agentroom-events"
    Module  = "SGA"
    Feature = "Agent Room Real-Time"
  }

  depends_on = [
    aws_iam_role_policy.eventbridge_pipe_source,
    aws_iam_role_policy.eventbridge_pipe_lambda
  ]
}

# =============================================================================
# Outputs
# =============================================================================

output "agentroom_pipe_arn" {
  description = "EventBridge Pipe ARN for Agent Room events"
  value       = aws_pipes_pipe.agent_room_events.arn
}

output "agentroom_enricher_function_name" {
  description = "Event enricher Lambda function name"
  value       = aws_lambda_function.event_enricher.function_name
}

output "agentroom_broadcast_function_name" {
  description = "WebSocket broadcast Lambda function name"
  value       = aws_lambda_function.websocket_broadcast.function_name
}
