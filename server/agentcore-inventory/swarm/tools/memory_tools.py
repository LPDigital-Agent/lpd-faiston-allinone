# =============================================================================
# Memory Tools - AgentCore Memory Integration for Inventory Swarm
# =============================================================================
# Tools for episodic memory management using AWS Bedrock AgentCore Memory.
#
# Used by: memory_agent
#
# Reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
# =============================================================================

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from strands import tool

logger = logging.getLogger(__name__)


@tool
def retrieve_episodes(
    query: str,
    file_type: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Retrieve prior import patterns from AgentCore Memory.

    Args:
        query: Search query (column names, file pattern, etc.)
        file_type: Optional filter by file type (csv, xlsx, etc.)
        limit: Maximum number of patterns to return

    Returns:
        dict with:
        - patterns: List of relevant prior import patterns
        - total_found: Total matching patterns
        - query_metadata: Search metadata
    """
    logger.info("[retrieve_episodes] Query: %s, file_type: %s", query, file_type)

    # In production, this would query AgentCore Memory
    # For now, return simulated patterns based on query
    try:
        from shared.agentcore_memory import AgentMemoryManager

        memory = AgentMemoryManager()
        episodes = memory.search_episodes(
            query=query,
            filters={"file_type": file_type} if file_type else None,
            limit=limit,
        )

        return {
            "patterns": episodes,
            "total_found": len(episodes),
            "query_metadata": {
                "query": query,
                "file_type": file_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    except ImportError:
        # Fallback for development - return mock patterns
        logger.warning("[retrieve_episodes] AgentMemoryManager not available, using mock")
        return _get_mock_patterns(query, file_type, limit)


@tool
def store_episode(
    file_pattern: str,
    file_type: str,
    column_mappings: List[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Store a successful import pattern in AgentCore Memory.

    Args:
        file_pattern: Pattern to match file names (regex or glob)
        file_type: File type (csv, xlsx, pdf, xml)
        column_mappings: Successful column mappings
        user_preferences: User preferences learned from this import

    Returns:
        dict with:
        - episode_id: ID of stored episode
        - success: Whether storage succeeded
        - message: Status message
    """
    logger.info(
        "[store_episode] Storing pattern for %s (%s)",
        file_pattern,
        file_type,
    )

    episode = {
        "episode_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file_pattern": file_pattern,
        "file_type": file_type,
        "column_mappings": column_mappings,
        "user_preferences": user_preferences or {},
        "success_count": 1,
        "last_used": datetime.now(timezone.utc).isoformat(),
    }

    try:
        from shared.agentcore_memory import AgentMemoryManager

        memory = AgentMemoryManager()
        memory.store_episode(episode)

        return {
            "episode_id": episode["episode_id"],
            "success": True,
            "message": f"Pattern stored successfully for {file_type} files",
        }

    except ImportError:
        logger.warning("[store_episode] AgentMemoryManager not available")
        return {
            "episode_id": episode["episode_id"],
            "success": True,
            "message": "Pattern stored (mock mode)",
        }


@tool
def get_adaptive_threshold(file_type: str) -> Dict[str, Any]:
    """
    Calculate adaptive confidence threshold based on historical accuracy.

    Args:
        file_type: File type to get threshold for

    Returns:
        dict with:
        - threshold: Recommended confidence threshold
        - basis: How threshold was calculated
        - historical_accuracy: Historical accuracy for this file type
    """
    logger.info("[get_adaptive_threshold] Calculating for file_type: %s", file_type)

    # Default thresholds
    default_thresholds = {
        "csv": 0.75,  # CSV is usually well-structured
        "xlsx": 0.80,  # Excel may have merged cells, formatting
        "pdf": 0.85,  # PDF extraction is less reliable
        "xml": 0.70,  # XML has clear structure
    }

    base_threshold = default_thresholds.get(file_type, 0.80)

    try:
        from shared.agentcore_memory import AgentMemoryManager

        memory = AgentMemoryManager()
        stats = memory.get_accuracy_stats(file_type)

        if stats and stats.get("total_imports", 0) > 5:
            # Adjust threshold based on historical accuracy
            accuracy = stats.get("accuracy", 0.0)
            if accuracy > 0.95:
                # High accuracy - can lower threshold
                threshold = max(0.65, base_threshold - 0.10)
            elif accuracy < 0.80:
                # Low accuracy - raise threshold
                threshold = min(0.90, base_threshold + 0.10)
            else:
                threshold = base_threshold

            return {
                "threshold": threshold,
                "basis": "Historical accuracy",
                "historical_accuracy": accuracy,
                "total_imports": stats.get("total_imports", 0),
            }

    except ImportError:
        pass

    return {
        "threshold": base_threshold,
        "basis": "Default for file type",
        "historical_accuracy": None,
        "total_imports": 0,
    }


@tool
def similarity_search(
    columns: List[str],
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Find similar past imports by column name similarity.

    Args:
        columns: List of column names from current file
        limit: Maximum number of similar patterns to return

    Returns:
        dict with:
        - similar_patterns: List of patterns with similarity scores
        - best_match: Highest similarity pattern
    """
    logger.info("[similarity_search] Searching with %d columns", len(columns))

    try:
        from shared.agentcore_memory import AgentMemoryManager

        memory = AgentMemoryManager()
        results = memory.similarity_search(
            column_names=columns,
            limit=limit,
        )

        return {
            "similar_patterns": results,
            "best_match": results[0] if results else None,
        }

    except ImportError:
        # Mock response
        return {
            "similar_patterns": [],
            "best_match": None,
            "message": "Similarity search not available (mock mode)",
        }


@tool
def update_pattern_success(
    episode_id: str,
    success: bool = True,
) -> Dict[str, Any]:
    """
    Update the success count for a pattern after import.

    Args:
        episode_id: ID of the episode to update
        success: Whether the import was successful

    Returns:
        dict with:
        - updated: Whether update succeeded
        - new_success_count: Updated success count
    """
    logger.info("[update_pattern_success] Updating %s (success=%s)", episode_id, success)

    try:
        from shared.agentcore_memory import AgentMemoryManager

        memory = AgentMemoryManager()
        result = memory.update_success_count(episode_id, success)

        return {
            "updated": True,
            "new_success_count": result.get("success_count", 0),
        }

    except ImportError:
        return {
            "updated": True,
            "new_success_count": 1,
            "message": "Updated (mock mode)",
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _get_mock_patterns(
    query: str,
    file_type: Optional[str],
    limit: int,
) -> Dict[str, Any]:
    """Return mock patterns for development."""
    # Simulate common patterns
    mock_patterns = [
        {
            "episode_id": "mock-001",
            "file_pattern": "EXPEDIÇÃO*.csv",
            "file_type": "csv",
            "column_mappings": [
                {"source": "PN", "target": "part_number", "confidence": 0.95},
                {"source": "SN", "target": "serial_number", "confidence": 0.95},
                {"source": "QTD", "target": "quantity", "confidence": 0.90},
            ],
            "user_preferences": {"unmapped_handling": "metadata"},
            "success_count": 10,
            "relevance_score": 0.85,
        },
        {
            "episode_id": "mock-002",
            "file_pattern": "ESTOQUE*.xlsx",
            "file_type": "xlsx",
            "column_mappings": [
                {"source": "PART_NUMBER", "target": "part_number", "confidence": 1.0},
                {"source": "SERIAL", "target": "serial_number", "confidence": 0.90},
                {"source": "QUANTIDADE", "target": "quantity", "confidence": 0.85},
            ],
            "user_preferences": {"date_format": "DD/MM/YYYY"},
            "success_count": 5,
            "relevance_score": 0.75,
        },
    ]

    # Filter by file_type if provided
    if file_type:
        mock_patterns = [p for p in mock_patterns if p["file_type"] == file_type]

    return {
        "patterns": mock_patterns[:limit],
        "total_found": len(mock_patterns),
        "query_metadata": {
            "query": query,
            "file_type": file_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "mock",
        },
    }
