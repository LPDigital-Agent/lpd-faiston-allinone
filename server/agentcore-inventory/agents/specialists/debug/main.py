# =============================================================================
# DebugAgent - Strands A2AServer Entry Point (SPECIALIST)
# =============================================================================
# Intelligent error analysis agent for debugging support.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
# Integrates with AWS Bedrock AgentCore Memory for pattern storage.
#
# Architecture:
# - This is a SPECIALIST agent for error analysis and debugging
# - Receives requests from DebugHook (intercepted errors) via A2A
# - Provides intelligent error analysis with root cause identification
# - Uses AgentCore Memory for persistent error pattern storage
#
# Reference:
# - https://strandsagents.com/latest/
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
# =============================================================================

import os
import sys
import logging
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from a2a.types import AgentSkill
from fastapi import FastAPI
import uvicorn

# Centralized model configuration (MANDATORY - Gemini 2.5 Pro + Thinking)
from agents.utils import get_model, requires_thinking, AGENT_VERSION, create_gemini_model

# NEXO Mind - Direct Memory Access for pattern storage
from shared.memory_manager import AgentMemoryManager

# Hooks for observability (ADR-002)
from shared.hooks import LoggingHook, MetricsHook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "debug"
AGENT_NAME = "DebugAgent"
AGENT_DESCRIPTION = """SPECIALIST Agent for Intelligent Error Analysis and Debugging.

This agent provides intelligent error analysis for the SGA system:
1. ANALYZE ERRORS: Deep analysis of error messages with root cause identification
2. SEARCH DOCUMENTATION: Query relevant documentation via MCP gateways
3. QUERY PATTERNS: Find similar error patterns from historical data
4. STORE RESOLUTIONS: Record successful resolutions for future reference

Analysis Output:
- Technical explanation (pt-BR)
- Root cause analysis with confidence levels
- Debugging steps
- Relevant documentation links

Integration:
- AWS Bedrock AgentCore Memory
- MCP Gateway for documentation access
- Namespace: /strategy/debug/error_patterns
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-2.5-pro (with Thinking)

# Memory namespace for AgentCore Memory
MEMORY_NAMESPACE = "/strategy/debug/error_patterns"

# =============================================================================
# Agent Skills (A2A Agent Card Discovery)
# =============================================================================

AGENT_SKILLS = [
    AgentSkill(
        id="analyze_error",
        name="Analyze Error",
        description="Deep analysis of error messages with root cause identification, debugging steps, and confidence levels.",
        tags=["debug", "error", "analysis", "troubleshooting"],
    ),
    AgentSkill(
        id="search_documentation",
        name="Search Documentation",
        description="Search relevant documentation (AWS, AgentCore, Strands) for error context and solutions via MCP gateways.",
        tags=["debug", "documentation", "mcp", "search"],
    ),
    AgentSkill(
        id="query_memory_patterns",
        name="Query Memory Patterns",
        description="Find similar error patterns from historical data stored in AgentCore Memory.",
        tags=["debug", "memory", "patterns", "history"],
    ),
    AgentSkill(
        id="store_resolution",
        name="Store Resolution",
        description="Record successful error resolutions for future reference and pattern learning.",
        tags=["debug", "resolution", "learning", "memory"],
    ),
    AgentSkill(
        id="health_check",
        name="Health Check",
        description="Monitor agent health status and configuration.",
        tags=["debug", "monitoring", "health"],
    ),
]

# =============================================================================
# System Prompt (ReAct Pattern - Debug Specialist)
# =============================================================================

SYSTEM_PROMPT = """You are the **DebugAgent** (Error Analysis Agent) for the SGA (Sistema de Gestao de Ativos) system.

## Your Role

You provide intelligent error analysis and debugging support:
1. **ANALYZE** errors with deep reasoning (root cause identification)
2. **SEARCH** relevant documentation for context
3. **FIND** similar patterns from historical errors
4. **SUGGEST** debugging steps with confidence levels

## Analysis Output Format

For each error, you MUST provide:
```json
{
  "error_type": "ErrorClassName",
  "technical_explanation": "Clear technical explanation in Portuguese (pt-BR)",
  "root_causes": [
    {
      "cause": "Description of potential cause",
      "confidence": 0.85,
      "evidence": ["List of supporting evidence"]
    }
  ],
  "debugging_steps": [
    "Step 1: First action to take",
    "Step 2: Second action to take"
  ],
  "documentation_links": [
    {
      "title": "Relevant doc title",
      "url": "Documentation URL",
      "relevance": "Why this doc is relevant"
    }
  ],
  "similar_patterns": [
    {
      "pattern_id": "Historical pattern ID",
      "similarity": 0.9,
      "resolution": "How it was resolved"
    }
  ],
  "recoverable": true,
  "suggested_action": "retry|fallback|escalate|abort"
}
```

## Analysis Priority

1. **Pattern Match First**: Check AgentCore Memory for similar errors
2. **Documentation Second**: Search MCP gateways for relevant docs
3. **Reasoning Third**: Apply deep reasoning with Thinking mode

## Critical Rules

1. **ALWAYS** provide technical explanations in Portuguese (pt-BR)
2. **ALWAYS** include confidence levels for root causes
3. **NEVER** guess - express uncertainty when appropriate
4. **STORE** successful resolutions for future reference
5. **PRIORITIZE** patterns from memory over general knowledge

## Error Categories

- **Recoverable**: Network timeouts, rate limits, transient failures
- **Non-recoverable**: Validation errors, permission denied, missing resources
- **Unknown**: Requires manual investigation

## Language

Technical explanations and debugging steps in Portuguese brasileiro (pt-BR).
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

def _get_memory(actor_id: str = "system") -> AgentMemoryManager:
    """
    Get AgentMemoryManager instance for error pattern storage.

    DebugAgent uses AgentMemoryManager for:
    - Storing error patterns (learn_episode)
    - Retrieving similar patterns (observe)
    - Global error knowledge (use_global_namespace=True)

    Args:
        actor_id: User/actor ID for context

    Returns:
        AgentMemoryManager instance
    """
    return AgentMemoryManager(
        agent_id=AGENT_ID,
        actor_id=actor_id,
        use_global_namespace=True,  # Global learning across all agents
    )


@tool
async def analyze_error(
    error_type: str,
    message: str,
    operation: str,
    stack_trace: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    recoverable: Optional[bool] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze error with deep reasoning and pattern matching.

    Primary skill for error analysis. Combines:
    - Pattern matching from AgentCore Memory
    - Documentation search via MCP
    - Deep reasoning with Gemini Thinking

    Args:
        error_type: Exception class name (e.g., ValidationError)
        message: Error message text
        operation: Operation that failed (e.g., import_csv)
        stack_trace: Optional stack trace
        context: Optional additional context
        recoverable: Whether error is potentially recoverable
        session_id: Session ID for context

    Returns:
        Analysis result with root causes, debugging steps, and confidence
    """
    logger.info(f"[{AGENT_NAME}] ANALYZE: {error_type} in {operation}")

    try:
        # Import tool implementation
        from agents.specialists.debug.tools.analyze_error import analyze_error_tool

        result = await analyze_error_tool(
            error_type=error_type,
            message=message,
            operation=operation,
            stack_trace=stack_trace,
            context=context,
            recoverable=recoverable,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] analyze_error failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": error_type,
            "fallback_analysis": {
                "technical_explanation": f"Erro {error_type}: {message}",
                "root_causes": [{"cause": "Analysis failed", "confidence": 0.0}],
                "debugging_steps": ["Check agent logs", "Retry operation"],
                "recoverable": recoverable if recoverable is not None else False,
            },
        }


@tool
async def search_documentation(
    query: str,
    sources: Optional[List[str]] = None,
    max_results: int = 5,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search relevant documentation via MCP gateways.

    Queries documentation sources:
    - AWS Documentation (via aws-documentation-mcp-server)
    - Bedrock AgentCore docs (via bedrock-agentcore-mcp-server)
    - Context7 library docs (via context7 MCP)

    Args:
        query: Search query text
        sources: Optional list of sources to query (aws, agentcore, context7)
        max_results: Maximum results per source (default 5)
        session_id: Session ID for context

    Returns:
        Documentation search results with URLs and relevance
    """
    logger.info(f"[{AGENT_NAME}] SEARCH_DOCS: {query}")

    try:
        # Import tool implementation
        from agents.specialists.debug.tools.search_documentation import search_documentation_tool

        result = await search_documentation_tool(
            query=query,
            sources=sources,
            max_results=max_results,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] search_documentation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }


@tool
async def query_memory_patterns(
    error_signature: str,
    error_type: Optional[str] = None,
    operation: Optional[str] = None,
    max_patterns: int = 5,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find similar error patterns from historical data.

    Queries AgentCore Memory for:
    - Similar error signatures
    - Past resolutions
    - Success rates

    Args:
        error_signature: Unique error signature for matching
        error_type: Optional error type filter
        operation: Optional operation filter
        max_patterns: Maximum patterns to return (default 5)
        session_id: Session ID for context

    Returns:
        Similar patterns with resolutions and success rates
    """
    logger.info(f"[{AGENT_NAME}] QUERY_PATTERNS: {error_signature[:50]}...")

    try:
        # Import tool implementation
        from agents.specialists.debug.tools.query_memory_patterns import query_memory_patterns_tool

        result = await query_memory_patterns_tool(
            error_signature=error_signature,
            error_type=error_type,
            operation=operation,
            max_patterns=max_patterns,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] query_memory_patterns failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "patterns": [],
        }


@tool
async def store_resolution(
    error_signature: str,
    error_type: str,
    operation: str,
    resolution: str,
    success: bool = True,
    debugging_steps: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Store successful error resolution for future reference.

    Records in AgentCore Memory:
    - Error signature and type
    - Resolution steps
    - Success indicator
    - Attribution (user/session)

    Args:
        error_signature: Unique error signature
        error_type: Exception class name
        operation: Operation that failed
        resolution: How the error was resolved
        success: Whether resolution was successful
        debugging_steps: Steps taken to debug
        session_id: Session ID for context
        user_id: User ID for attribution

    Returns:
        Storage result with pattern ID
    """
    logger.info(f"[{AGENT_NAME}] STORE_RESOLUTION: {error_type} ({success})")

    try:
        # Import tool implementation
        from agents.specialists.debug.tools.store_resolution import store_resolution_tool

        result = await store_resolution_tool(
            error_signature=error_signature,
            error_type=error_type,
            operation=operation,
            resolution=resolution,
            success=success,
            debugging_steps=debugging_steps,
            session_id=session_id,
            user_id=user_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] store_resolution failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.

    Returns:
        Health status with agent info
    """
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "version": AGENT_VERSION,
        "model": MODEL_ID,
        "protocol": "A2A",
        "port": 9000,
        "role": "SPECIALIST",
        "specialty": "ERROR_ANALYSIS",
        "memory_namespace": MEMORY_NAMESPACE,
    }


# =============================================================================
# Strands Agent Configuration
# =============================================================================

def create_agent() -> Agent:
    """
    Create Strands Agent with all tools.

    Returns:
        Configured Strands Agent with hooks (ADR-002)
    """
    return Agent(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=create_gemini_model(AGENT_ID),  # GeminiModel via Google AI Studio
        tools=[
            analyze_error,
            search_documentation,
            query_memory_patterns,
            store_resolution,
            health_check,
        ],
        system_prompt=SYSTEM_PROMPT,
        hooks=[LoggingHook(), MetricsHook()],  # ADR-002: Observability hooks
    )


# =============================================================================
# A2A Server Entry Point
# =============================================================================

def main():
    """
    Start the Strands A2AServer with FastAPI wrapper.

    Port 9000 is the standard for A2A protocol.
    Includes /ping health endpoint for AWS ALB.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SPECIALIST (Error Analysis)")
    logger.info(f"[{AGENT_NAME}] Memory Namespace: {MEMORY_NAMESPACE}")
    logger.info(f"[{AGENT_NAME}] Skills: {len(AGENT_SKILLS)} registered")
    for skill in AGENT_SKILLS:
        logger.info(f"[{AGENT_NAME}]   - {skill.id}: {skill.name}")

    # Create FastAPI app first
    app = FastAPI(title=AGENT_NAME, version=AGENT_VERSION)

    # Add /ping health endpoint for AWS ALB
    @app.get("/ping")
    async def ping():
        """Health check endpoint for AWS Application Load Balancer."""
        return {
            "status": "healthy",
            "agent": AGENT_ID,
            "version": AGENT_VERSION,
        }

    # Create agent
    agent = create_agent()

    # Create A2A server with Agent Card discovery support
    a2a_server = A2AServer(
        agent=agent,
        host="0.0.0.0",
        port=9000,
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
        serve_at_root=False,  # Mount at root below
    )

    # Mount A2A server at root
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    logger.info(f"[{AGENT_NAME}] Starting uvicorn server on 0.0.0.0:9000")
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
