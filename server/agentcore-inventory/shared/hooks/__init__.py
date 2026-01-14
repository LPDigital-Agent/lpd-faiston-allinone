"""
Faiston SGA Agent Hooks

HookProvider implementations for Strands Agents:
- LoggingHook: Structured logging for all agent events
- MetricsHook: CloudWatch metrics emission
- GuardrailsHook: Shadow mode content moderation

Usage:
    from shared.hooks import LoggingHook, MetricsHook

    agent = Agent(
        hooks=[LoggingHook(), MetricsHook()]
    )
"""
from .logging_hook import LoggingHook
from .metrics_hook import MetricsHook
from .guardrails_hook import GuardrailsHook

__all__ = ["LoggingHook", "MetricsHook", "GuardrailsHook"]
