# =============================================================================
# NexoImportAgent - Main Orchestrator
# =============================================================================
# Intelligent import assistant using ReAct pattern.
#
# This is the MAIN ORCHESTRATOR that coordinates the import flow:
# - Delegates to LearningAgent for memory operations (via A2A)
# - Delegates to SchemaEvolutionAgent for column creation (via A2A)
# - Uses ADK tools for file analysis and import execution
#
# Architecture:
# - Runtime: Dedicated AgentCore Runtime (1 runtime = 1 agent)
# - Protocol: A2A (JSON-RPC 2.0) for inter-agent communication
# - Memory: Delegates to LearningAgent (no direct memory access)
# =============================================================================

from agents.nexo_import.agent import create_nexo_import_agent, AGENT_ID, AGENT_NAME

__all__ = [
    "create_nexo_import_agent",
    "AGENT_ID",
    "AGENT_NAME",
]
