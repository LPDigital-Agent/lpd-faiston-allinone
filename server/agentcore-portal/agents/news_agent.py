# =============================================================================
# News Agent - Faiston Portal
# =============================================================================
# RSS/API news aggregation agent for tech news feed.
#
# Sources:
# - Cloud providers: AWS, Azure, Google Cloud
# - Tech news: TechCrunch AI, Hacker News
# - Brazil: TechTudo, Canaltech
#
# Framework: Google ADK with Gemini 3.0 Pro
# =============================================================================

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class NewsAgent:
    """
    Tech news aggregation agent.

    Fetches and aggregates news from multiple RSS feeds,
    with optional AI-powered relevance scoring.
    """

    def __init__(self):
        """Initialize NewsAgent."""
        # Lazy import utils to avoid cold start penalty
        from agents.utils import (
            NEWS_SOURCES,
            DEFAULT_NEWS_CATEGORIES,
            MAX_ARTICLES_PER_SOURCE,
            MAX_TOTAL_ARTICLES
        )
        self.news_sources = NEWS_SOURCES
        self.default_categories = DEFAULT_NEWS_CATEGORIES
        self.max_per_source = MAX_ARTICLES_PER_SOURCE
        self.max_total = MAX_TOTAL_ARTICLES

    async def get_aggregated_feed(
        self,
        categories: Optional[List[str]] = None,
        max_articles: Optional[int] = None,
        language: str = "all"
    ) -> Dict[str, Any]:
        """
        Aggregate news from multiple RSS sources.

        Args:
            categories: List of categories to fetch (default: all)
            max_articles: Maximum total articles to return
            language: Filter by language ("all", "en", "pt-br")

        Returns:
            Aggregated news feed response
        """
        from tools.rss_parser import fetch_multiple_feeds

        categories = categories or self.default_categories
        max_articles = max_articles or self.max_total

        all_articles = []
        fetch_errors = []

        # Fetch feeds for each category in parallel
        for category in categories:
            sources = self.news_sources.get(category, [])

            # Filter by language if specified
            if language != "all":
                sources = [
                    s for s in sources
                    if s.get("language", "en") == language
                ]

            if not sources:
                continue

            try:
                articles = await fetch_multiple_feeds(
                    sources=sources,
                    category=category,
                    max_per_source=self.max_per_source
                )
                all_articles.extend(articles)
            except Exception as e:
                fetch_errors.append({
                    "category": category,
                    "error": str(e)
                })

        # Sort by published date (newest first)
        all_articles.sort(
            key=lambda x: x.get("publishedAt", ""),
            reverse=True
        )

        # Limit total articles
        all_articles = all_articles[:max_articles]

        return {
            "success": True,
            "articles": all_articles,
            "count": len(all_articles),
            "categories_fetched": categories,
            "errors": fetch_errors if fetch_errors else None,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

    async def get_news_by_category(
        self,
        category: str,
        max_articles: int = 10
    ) -> Dict[str, Any]:
        """
        Get news for a specific category.

        Args:
            category: Category to fetch (cloud-aws, ai, brazil, etc.)
            max_articles: Maximum articles to return

        Returns:
            News feed for the category
        """
        return await self.get_aggregated_feed(
            categories=[category],
            max_articles=max_articles
        )

    async def search_news(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        max_articles: int = 10
    ) -> Dict[str, Any]:
        """
        Search news articles by keyword.

        Args:
            query: Search query
            categories: Categories to search in
            max_articles: Maximum results

        Returns:
            Filtered news articles matching query
        """
        # First, fetch all articles
        feed = await self.get_aggregated_feed(
            categories=categories,
            max_articles=100  # Fetch more for filtering
        )

        if not feed.get("success"):
            return feed

        # Filter by query (case-insensitive)
        query_lower = query.lower()
        filtered = [
            article for article in feed["articles"]
            if query_lower in article.get("title", "").lower()
            or query_lower in article.get("summary", "").lower()
        ]

        return {
            "success": True,
            "articles": filtered[:max_articles],
            "count": len(filtered[:max_articles]),
            "query": query,
            "total_matches": len(filtered)
        }

    async def get_daily_summary(
        self,
        categories: Optional[List[str]] = None,
        max_per_category: int = 3
    ) -> Dict[str, Any]:
        """
        Get a summarized daily news digest.

        Args:
            categories: Categories to include
            max_per_category: Max articles per category

        Returns:
            Daily digest with top articles per category
        """
        categories = categories or self.default_categories
        digest = {}

        for category in categories:
            result = await self.get_news_by_category(
                category=category,
                max_articles=max_per_category
            )

            if result.get("success"):
                digest[category] = {
                    "articles": result["articles"],
                    "count": len(result["articles"])
                }

        # Calculate totals
        total_articles = sum(
            cat.get("count", 0) for cat in digest.values()
        )

        return {
            "success": True,
            "digest": digest,
            "total_articles": total_articles,
            "categories": list(digest.keys()),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# =============================================================================
# Module-level functions for direct invocation
# =============================================================================

async def get_tech_news(
    categories: Optional[List[str]] = None,
    max_articles: int = 20,
    language: str = "all"
) -> Dict[str, Any]:
    """
    Convenience function to get tech news.

    Used by main.py handler for direct invocation.
    """
    agent = NewsAgent()
    return await agent.get_aggregated_feed(
        categories=categories,
        max_articles=max_articles,
        language=language
    )


async def get_news_digest() -> Dict[str, Any]:
    """
    Convenience function to get daily news digest.

    Used by main.py handler for daily summary.
    """
    agent = NewsAgent()
    return await agent.get_daily_summary()
