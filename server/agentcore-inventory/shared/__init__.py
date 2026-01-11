# =============================================================================
# Shared Module - Common Utilities for All SGA Agents
# =============================================================================
# This module provides shared infrastructure for the 100% Agentic architecture:
#
# - audit_emitter: Agent Room real-time visibility (DynamoDB audit trail)
# - a2a_client: A2A protocol client (JSON-RPC 2.0)
# - xray_tracer: X-Ray distributed tracing
#
# Usage:
#   from shared.audit_emitter import AgentAuditEmitter, AgentStatus
#   from shared.a2a_client import A2AClient, delegate_to_learning
#   from shared.xray_tracer import trace_a2a_call, init_xray_tracing
#
# Architecture: Google ADK + AWS Bedrock AgentCore (100% Agentic)
# =============================================================================

# Audit Emitter exports
from shared.audit_emitter import (
    AgentAuditEmitter,
    AgentStatus,
    AuditEvent,
    emit_agent_event,
)

# A2A Client exports
from shared.a2a_client import (
    A2AClient,
    A2AMessage,
    A2AResponse,
    delegate_to_learning,
    delegate_to_validation,
    delegate_to_schema_evolution,
)

# X-Ray Tracer exports
from shared.xray_tracer import (
    init_xray_tracing,
    trace_a2a_call,
    trace_memory_operation,
    trace_tool_call,
    trace_subsegment,
    add_trace_annotation,
    add_trace_metadata,
)

__all__ = [
    # Audit Emitter
    "AgentAuditEmitter",
    "AgentStatus",
    "AuditEvent",
    "emit_agent_event",
    # A2A Client
    "A2AClient",
    "A2AMessage",
    "A2AResponse",
    "delegate_to_learning",
    "delegate_to_validation",
    "delegate_to_schema_evolution",
    # X-Ray Tracer
    "init_xray_tracing",
    "trace_a2a_call",
    "trace_memory_operation",
    "trace_tool_call",
    "trace_subsegment",
    "add_trace_annotation",
    "add_trace_metadata",
]
