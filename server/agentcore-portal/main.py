# =============================================================================
# AWS Bedrock AgentCore Runtime Entrypoint - Faiston Portal
# =============================================================================
# Main entrypoint for Faiston Portal agents deployed to AgentCore Runtime.
# Uses BedrockAgentCoreApp decorator pattern for serverless deployment.
#
# Framework: Google ADK with native Gemini 3.0 Pro (no LiteLLM wrapper)
# Model: All agents use gemini-3-pro-preview exclusively (MANDATORY)
#
# Purpose: Central AI orchestrator for the Faiston NEXO intranet
# - News aggregation (RSS feeds)
# - A2A delegation to Academy and SGA agents
# - Daily summary generation
# - General chat assistance
#
# OPTIMIZATION: Lazy imports for faster cold start
# Agents are imported only when needed, reducing initialization time from ~30s to ~10s.
# This is critical for AgentCore Runtime's 30-second initialization limit.
#
# Based on:
# - https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/03-integrations/agentic-frameworks/adk
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html
# =============================================================================

# Note: GOOGLE_API_KEY is passed via --env at deploy time (not runtime SSM lookup)
# This follows the AWS official example pattern.

from bedrock_agentcore.runtime import BedrockAgentCoreApp
import asyncio
import json
import os
from datetime import datetime, timezone

# LAZY IMPORTS: Agents are imported inside handler functions to reduce cold start time.
# Each agent imports Google ADK packages (~3-5s each), so importing all at startup = ~10-15s.
# By lazy loading, we only pay the import cost for the agent actually being used.

# =============================================================================
# AgentCore Application
# =============================================================================

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """
    Main entrypoint for AgentCore Runtime.

    Routes requests to the appropriate handler based on the 'action' field.

    Args:
        payload: Request payload containing action and parameters
        context: AgentCore context with session_id, etc.

    Returns:
        Agent response as dict
    """
    action = payload.get("action", "health_check")
    user_id = payload.get("user_id", "anonymous")
    session_id = getattr(context, "session_id", "default-session")

    # Route to appropriate handler
    try:
        # =============================================================================
        # Core Actions
        # =============================================================================

        if action == "health_check":
            return _health_check()

        elif action == "nexo_chat":
            return asyncio.run(_nexo_chat(payload, user_id, session_id))

        elif action == "get_daily_summary":
            return asyncio.run(_get_daily_summary(payload, user_id))

        # =============================================================================
        # News Actions
        # =============================================================================

        elif action == "get_tech_news":
            return asyncio.run(_get_tech_news(payload))

        elif action == "get_news_by_category":
            return asyncio.run(_get_news_by_category(payload))

        elif action == "search_news":
            return asyncio.run(_search_news(payload))

        elif action == "get_news_digest":
            return asyncio.run(_get_news_digest())

        # =============================================================================
        # A2A Delegation Actions
        # =============================================================================

        elif action == "delegate_to_academy":
            return asyncio.run(_delegate_to_academy(payload, user_id, session_id))

        elif action == "delegate_to_sga":
            return asyncio.run(_delegate_to_sga(payload, user_id, session_id))

        # =============================================================================
        # Unknown Action
        # =============================================================================

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e), "action": action}


# =============================================================================
# Core Handlers
# =============================================================================

def _health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "module": "Faiston Portal AgentCore",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "capabilities": [
            "nexo_chat",
            "get_daily_summary",
            "get_tech_news",
            "get_news_by_category",
            "search_news",
            "get_news_digest",
            "delegate_to_academy",
            "delegate_to_sga"
        ]
    }


async def _nexo_chat(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Handle NEXO chat message.

    Payload:
        question: str - User's message
        conversation_history: List[Dict] - Optional previous messages
    """
    from agents.nexo_orchestrator_agent import nexo_chat

    question = payload.get("question", "")
    if not question:
        return {"error": "Missing required field: question"}

    conversation_history = payload.get("conversation_history")

    return await nexo_chat(
        question=question,
        user_id=user_id,
        session_id=session_id,
        conversation_history=conversation_history
    )


async def _get_daily_summary(payload: dict, user_id: str) -> dict:
    """
    Get personalized daily summary.

    Payload:
        include_news: bool - Include news digest (default: True)
    """
    from agents.nexo_orchestrator_agent import get_daily_summary

    include_news = payload.get("include_news", True)

    return await get_daily_summary(
        user_id=user_id,
        include_news=include_news
    )


# =============================================================================
# News Handlers
# =============================================================================

async def _get_tech_news(payload: dict) -> dict:
    """
    Get aggregated tech news.

    Payload:
        categories: List[str] - Categories to fetch (optional)
        max_articles: int - Maximum articles (default: 20)
        language: str - Language filter (default: "all")
    """
    from agents.news_agent import get_tech_news

    categories = payload.get("categories")
    max_articles = payload.get("max_articles", 20)
    language = payload.get("language", "all")

    return await get_tech_news(
        categories=categories,
        max_articles=max_articles,
        language=language
    )


async def _get_news_by_category(payload: dict) -> dict:
    """
    Get news for a specific category.

    Payload:
        category: str - Category to fetch (required)
        max_articles: int - Maximum articles (default: 10)
    """
    from agents.news_agent import NewsAgent

    category = payload.get("category")
    if not category:
        return {"error": "Missing required field: category"}

    max_articles = payload.get("max_articles", 10)

    agent = NewsAgent()
    return await agent.get_news_by_category(
        category=category,
        max_articles=max_articles
    )


async def _search_news(payload: dict) -> dict:
    """
    Search news by keyword.

    Payload:
        query: str - Search query (required)
        categories: List[str] - Categories to search (optional)
        max_articles: int - Maximum results (default: 10)
    """
    from agents.news_agent import NewsAgent

    query = payload.get("query")
    if not query:
        return {"error": "Missing required field: query"}

    categories = payload.get("categories")
    max_articles = payload.get("max_articles", 10)

    agent = NewsAgent()
    return await agent.search_news(
        query=query,
        categories=categories,
        max_articles=max_articles
    )


async def _get_news_digest() -> dict:
    """Get daily news digest."""
    from agents.news_agent import get_news_digest
    return await get_news_digest()


# =============================================================================
# A2A Delegation Handlers
# =============================================================================

async def _delegate_to_academy(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Delegate question to Academy AgentCore.

    Payload:
        question: str - Question to ask Academy (required)
        context: Dict - Additional context (optional)
    """
    from tools.a2a_client import delegate_to_academy

    question = payload.get("question")
    if not question:
        return {"error": "Missing required field: question"}

    context = payload.get("context")

    return await delegate_to_academy(
        question=question,
        user_id=user_id,
        session_id=session_id,
        context=context
    )


async def _delegate_to_sga(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Delegate question to SGA Inventory AgentCore.

    Payload:
        question: str - Question to ask SGA (required)
        context: Dict - Additional context (optional)
    """
    from tools.a2a_client import delegate_to_sga

    question = payload.get("question")
    if not question:
        return {"error": "Missing required field: question"}

    context = payload.get("context")

    return await delegate_to_sga(
        question=question,
        user_id=user_id,
        session_id=session_id,
        context=context
    )


# =============================================================================
# Main (for local testing)
# =============================================================================

if __name__ == "__main__":
    app.run()
