# =============================================================================
# RSS Feed Parser Tool - Faiston Portal
# =============================================================================
# Lightweight RSS/Atom feed parser for news aggregation.
#
# Uses feedparser library for reliable parsing across different feed formats.
# Falls back to stdlib xml.etree.ElementTree for minimal dependency scenarios.
# =============================================================================

import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncio


async def fetch_and_parse_feed(
    url: str,
    source_name: str,
    source_icon: str,
    category: str,
    max_articles: int = 10,
    timeout: int = 15
) -> List[Dict[str, Any]]:
    """
    Fetch and parse an RSS/Atom feed asynchronously.

    Args:
        url: Feed URL to fetch
        source_name: Display name of the source
        source_icon: Icon identifier for the source
        category: Category classification (cloud-aws, ai, etc.)
        max_articles: Maximum number of articles to return
        timeout: Request timeout in seconds

    Returns:
        List of article dictionaries with standardized format
    """
    import httpx
    import feedparser

    articles = []

    try:
        # Fetch feed content
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "FaistonNEXO/1.0 (News Aggregator)"
                }
            )
            response.raise_for_status()
            content = response.text

        # Parse with feedparser
        feed = feedparser.parse(content)

        if feed.bozo and not feed.entries:
            # Feed parsing error with no entries
            print(f"[RSS] Warning: Feed parsing issue for {source_name}: {feed.bozo_exception}")
            return []

        # Process entries
        for entry in feed.entries[:max_articles]:
            try:
                article = _parse_entry(entry, source_name, source_icon, category)
                if article:
                    articles.append(article)
            except Exception as e:
                print(f"[RSS] Error parsing entry from {source_name}: {e}")
                continue

    except httpx.TimeoutException:
        print(f"[RSS] Timeout fetching {source_name}: {url}")
    except httpx.HTTPStatusError as e:
        print(f"[RSS] HTTP error fetching {source_name}: {e.response.status_code}")
    except Exception as e:
        print(f"[RSS] Error fetching {source_name}: {e}")

    return articles


def _parse_entry(
    entry: Any,
    source_name: str,
    source_icon: str,
    category: str
) -> Optional[Dict[str, Any]]:
    """
    Parse a single feed entry into standardized article format.

    Args:
        entry: feedparser entry object
        source_name: Display name of the source
        source_icon: Icon identifier
        category: Category classification

    Returns:
        Article dictionary or None if parsing fails
    """
    # Extract link
    link = entry.get("link", "")
    if not link:
        return None

    # Generate unique ID from link
    article_id = hashlib.md5(link.encode()).hexdigest()[:12]

    # Extract title
    title = entry.get("title", "").strip()
    if not title:
        return None

    # Extract summary/description
    summary = ""
    if "summary" in entry:
        summary = entry.summary
    elif "description" in entry:
        summary = entry.description
    elif "content" in entry and entry.content:
        summary = entry.content[0].get("value", "")

    # Clean HTML from summary
    summary = _strip_html_tags(summary)
    summary = summary[:300]  # Limit length

    # Extract published date
    published_at = ""
    if "published" in entry:
        published_at = entry.published
    elif "updated" in entry:
        published_at = entry.updated
    elif "pubDate" in entry:
        published_at = entry.pubDate

    # Try to parse and format date
    try:
        if "published_parsed" in entry and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6])
            published_at = dt.isoformat() + "Z"
        elif "updated_parsed" in entry and entry.updated_parsed:
            dt = datetime(*entry.updated_parsed[:6])
            published_at = dt.isoformat() + "Z"
    except Exception:
        pass  # Keep original string if parsing fails

    # Calculate read time (roughly 200 words per minute)
    word_count = len(summary.split())
    read_time = max(2, word_count // 200 + 1)

    # Extract author
    author = entry.get("author", "")

    return {
        "id": article_id,
        "title": title,
        "source": source_name,
        "sourceIcon": source_icon,
        "category": category,
        "summary": summary,
        "url": link,
        "publishedAt": published_at,
        "readTime": read_time,
        "author": author,
        "relevanceScore": 80,  # Default score, can be enhanced with AI scoring later
    }


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&#39;', "'")
    # Normalize whitespace
    clean = ' '.join(clean.split())
    return clean.strip()


async def fetch_multiple_feeds(
    sources: List[Dict[str, str]],
    category: str,
    max_per_source: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch multiple feeds in parallel.

    Args:
        sources: List of source configurations
        category: Category for all sources
        max_per_source: Maximum articles per source

    Returns:
        Combined list of articles from all sources
    """
    tasks = []
    for source in sources:
        task = fetch_and_parse_feed(
            url=source["url"],
            source_name=source["name"],
            source_icon=source["icon"],
            category=category,
            max_articles=max_per_source
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    articles = []
    for result in results:
        if isinstance(result, list):
            articles.extend(result)
        elif isinstance(result, Exception):
            print(f"[RSS] Feed fetch failed: {result}")

    return articles
