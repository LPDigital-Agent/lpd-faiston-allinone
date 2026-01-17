# =============================================================================
# DebugAgent Tools - Module Exports
# =============================================================================
# Tool implementations for the DebugAgent specialist.
#
# Tools:
# - analyze_error: Deep error analysis with root cause identification
# - search_documentation: MCP-based documentation search
# - query_memory_patterns: Historical error pattern lookup
# - store_resolution: Store successful resolutions
# =============================================================================

from agents.specialists.debug.tools.analyze_error import analyze_error_tool
from agents.specialists.debug.tools.search_documentation import search_documentation_tool
from agents.specialists.debug.tools.query_memory_patterns import query_memory_patterns_tool
from agents.specialists.debug.tools.store_resolution import store_resolution_tool

__all__ = [
    "analyze_error_tool",
    "search_documentation_tool",
    "query_memory_patterns_tool",
    "store_resolution_tool",
]
