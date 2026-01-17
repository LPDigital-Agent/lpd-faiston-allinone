# =============================================================================
# DebugAgent Tool: search_documentation
# =============================================================================
# Search relevant documentation via MCP gateways.
#
# Sources:
# - AWS Documentation (via aws-documentation-mcp-server)
# - Bedrock AgentCore docs (via bedrock-agentcore-mcp-server)
# - Context7 library docs (via context7 MCP)
#
# Note: In production, this tool will use MCP Gateway to access
# documentation servers. For now, it provides structured search results
# based on common error patterns.
# =============================================================================

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Common documentation mappings for quick lookup
DOC_MAPPINGS = {
    "agentcore": {
        "memory": [
            {
                "title": "AgentCore Memory - Getting Started",
                "url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html",
                "relevance": "Guia principal de uso do AgentCore Memory",
            },
            {
                "title": "Memory Namespace Configuration",
                "url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-namespaces.html",
                "relevance": "Configuração de namespaces para isolamento de dados",
            },
        ],
        "runtime": [
            {
                "title": "AgentCore Runtime - Deployment",
                "url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html",
                "relevance": "Deploy de agentes no AgentCore Runtime",
            },
        ],
        "gateway": [
            {
                "title": "AgentCore Gateway - MCP Integration",
                "url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html",
                "relevance": "Integração com MCP Gateway",
            },
        ],
    },
    "strands": {
        "agent": [
            {
                "title": "Strands Agents - Quick Start",
                "url": "https://strandsagents.com/latest/documentation/docs/getting-started/",
                "relevance": "Guia de início rápido para Strands Agents",
            },
        ],
        "a2a": [
            {
                "title": "A2A Protocol - Agent Communication",
                "url": "https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multiagent/a2a/",
                "relevance": "Comunicação entre agentes via A2A",
            },
        ],
        "hooks": [
            {
                "title": "Strands Hooks - Lifecycle Events",
                "url": "https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/hooks/",
                "relevance": "Hooks para interceptar eventos do ciclo de vida",
            },
        ],
    },
    "gemini": {
        "thinking": [
            {
                "title": "Gemini Thinking Mode",
                "url": "https://ai.google.dev/gemini-api/docs/thinking",
                "relevance": "Modo de raciocínio profundo do Gemini",
            },
        ],
        "api": [
            {
                "title": "Gemini API Reference",
                "url": "https://ai.google.dev/gemini-api/docs/models/gemini",
                "relevance": "Referência da API Gemini",
            },
        ],
    },
}


async def search_documentation_tool(
    query: str,
    sources: Optional[List[str]] = None,
    max_results: int = 5,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search relevant documentation via MCP gateways.

    In production, this will use AgentCore Gateway to access:
    - aws-documentation-mcp-server
    - bedrock-agentcore-mcp-server
    - context7 MCP server

    For now, it provides structured search results based on
    keyword matching against common documentation mappings.

    Args:
        query: Search query text
        sources: Optional list of sources to query
        max_results: Maximum results per source
        session_id: Session ID for context

    Returns:
        Documentation search results with URLs and relevance
    """
    logger.info(f"[search_documentation] Query: {query[:50]}...")

    if sources is None:
        sources = ["agentcore", "strands", "gemini"]

    results = []
    query_lower = query.lower()

    # Extract keywords from query
    keywords = _extract_keywords(query_lower)

    # Search each source
    for source in sources:
        if source == "aws" or source == "agentcore":
            results.extend(_search_agentcore_docs(keywords, max_results))
        elif source == "strands":
            results.extend(_search_strands_docs(keywords, max_results))
        elif source == "gemini":
            results.extend(_search_gemini_docs(keywords, max_results))

    # Deduplicate and limit results
    seen_urls = set()
    unique_results = []
    for result in results:
        if result["url"] not in seen_urls:
            seen_urls.add(result["url"])
            unique_results.append(result)
            if len(unique_results) >= max_results:
                break

    return {
        "success": True,
        "query": query,
        "sources_searched": sources,
        "results": unique_results,
        "total_found": len(unique_results),
    }


def _extract_keywords(query: str) -> List[str]:
    """
    Extract keywords from search query.

    Args:
        query: Search query string

    Returns:
        List of keywords
    """
    # Common keywords to look for
    keyword_map = {
        "memory": ["memory", "memória", "armazenamento", "storage"],
        "runtime": ["runtime", "deploy", "deployment", "execução"],
        "gateway": ["gateway", "mcp", "tool", "ferramenta"],
        "agent": ["agent", "agente", "strands"],
        "a2a": ["a2a", "protocol", "communication", "comunicação"],
        "hooks": ["hook", "lifecycle", "event", "evento"],
        "thinking": ["thinking", "raciocínio", "reasoning"],
        "api": ["api", "reference", "referência"],
    }

    found_keywords = []
    for keyword, variations in keyword_map.items():
        if any(v in query for v in variations):
            found_keywords.append(keyword)

    return found_keywords if found_keywords else ["agent"]  # Default


def _search_agentcore_docs(
    keywords: List[str],
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search AgentCore documentation."""
    results = []

    for keyword in keywords:
        if keyword in DOC_MAPPINGS["agentcore"]:
            for doc in DOC_MAPPINGS["agentcore"][keyword]:
                results.append({
                    "source": "agentcore",
                    **doc,
                })

    return results[:max_results]


def _search_strands_docs(
    keywords: List[str],
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search Strands documentation."""
    results = []

    for keyword in keywords:
        if keyword in DOC_MAPPINGS["strands"]:
            for doc in DOC_MAPPINGS["strands"][keyword]:
                results.append({
                    "source": "strands",
                    **doc,
                })

    return results[:max_results]


def _search_gemini_docs(
    keywords: List[str],
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search Gemini documentation."""
    results = []

    for keyword in keywords:
        if keyword in DOC_MAPPINGS["gemini"]:
            for doc in DOC_MAPPINGS["gemini"][keyword]:
                results.append({
                    "source": "gemini",
                    **doc,
                })

    return results[:max_results]
