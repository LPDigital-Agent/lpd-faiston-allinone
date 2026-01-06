# =============================================================================
# Faiston Portal Agents - Shared Utilities
# =============================================================================
# Constants, configurations, and utility functions shared across portal agents.
#
# Note: Keep this file lightweight - no heavy imports allowed.
# =============================================================================

import os
from typing import Dict, List, Any

# =============================================================================
# Model Configuration
# =============================================================================

# MANDATORY: Use only Gemini 3.0 Family (per CLAUDE.md instructions)
MODEL_ID = "gemini-3-pro-preview"
MODEL_FAMILY = "gemini-3"

# =============================================================================
# A2A Agent Configuration
# =============================================================================

# Academy AgentCore ARN (deployed)
ACADEMY_AGENTCORE_ARN = os.environ.get(
    "ACADEMY_AGENTCORE_ARN",
    "arn:aws:bedrock-agentcore:us-east-2:377311924364:runtime/faiston_academy_agents-ODNvP6HxCD"
)

# SGA Inventory AgentCore ARN (deployed)
SGA_AGENTCORE_ARN = os.environ.get(
    "SGA_AGENTCORE_ARN",
    "arn:aws:bedrock-agentcore:us-east-2:377311924364:runtime/faiston_sga_inventory-PLACEHOLDER"
)

# AWS Region for AgentCore
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

# =============================================================================
# News Feed Configuration
# =============================================================================

NEWS_SOURCES: Dict[str, List[Dict[str, str]]] = {
    "cloud-aws": [
        {
            "url": "https://aws.amazon.com/blogs/aws/feed/",
            "name": "AWS News Blog",
            "icon": "aws",
            "language": "en"
        },
    ],
    "cloud-azure": [
        {
            "url": "https://azure.microsoft.com/en-us/blog/feed/",
            "name": "Azure Blog",
            "icon": "azure",
            "language": "en"
        },
    ],
    "cloud-gcp": [
        {
            "url": "https://cloud.google.com/feeds/blog.xml",
            "name": "Google Cloud Blog",
            "icon": "google",
            "language": "en"
        },
    ],
    "ai": [
        {
            "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
            "name": "TechCrunch AI",
            "icon": "techcrunch",
            "language": "en"
        },
        {
            "url": "https://news.ycombinator.com/rss",
            "name": "Hacker News",
            "icon": "hackernews",
            "language": "en"
        },
    ],
    "brazil": [
        {
            "url": "https://www.techtudo.com.br/rss/feed.xml",
            "name": "TechTudo",
            "icon": "techtudo",
            "language": "pt-br"
        },
        {
            "url": "https://canaltech.com.br/rss/",
            "name": "Canaltech",
            "icon": "canaltech",
            "language": "pt-br"
        },
    ],
}

# Default categories for news feed
DEFAULT_NEWS_CATEGORIES = ["cloud-aws", "cloud-gcp", "cloud-azure", "ai"]

# Maximum articles per source
MAX_ARTICLES_PER_SOURCE = 10

# Maximum total articles to return
MAX_TOTAL_ARTICLES = 30

# =============================================================================
# Agent Response Helpers
# =============================================================================

def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Create a standardized success response."""
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(error: str, code: str = "UNKNOWN_ERROR") -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "success": False,
        "error": error,
        "code": code
    }


def classify_query_domain(query: str) -> str:
    """
    Classify user query to determine which domain it belongs to.

    Returns:
        - "academy" for learning/education queries
        - "inventory" for stock/asset queries
        - "portal" for general queries (news, calendar, etc.)
    """
    query_lower = query.lower()

    # Academy keywords (Portuguese and English)
    academy_keywords = [
        "curso", "aula", "treinamento", "flashcard", "mindmap", "mapa mental",
        "aprender", "estudar", "podcast", "audio", "video aula", "slide",
        "course", "lesson", "training", "learn", "study", "education"
    ]

    # Inventory keywords (Portuguese and English)
    inventory_keywords = [
        "estoque", "ativo", "material", "entrada", "saida", "transferencia",
        "inventario", "nf", "nota fiscal", "expedicao", "reversa",
        "stock", "asset", "material", "inventory", "warehouse", "shipping"
    ]

    # Check for academy domain
    if any(kw in query_lower for kw in academy_keywords):
        return "academy"

    # Check for inventory domain
    if any(kw in query_lower for kw in inventory_keywords):
        return "inventory"

    # Default to portal (news, general assistance)
    return "portal"
