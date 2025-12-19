# =============================================================================
# YouTube Data API v3 Tool - Video Search
# =============================================================================
# YouTube integration for searching educational videos to supplement lesson content.
#
# API: YouTube Data API v3
# Endpoint: search.list (100 quota units per call)
# Daily Quota: 10,000 units (free tier)
#
# Usage Pattern:
# - Search for educational videos related to lesson topics
# - Return video metadata (id, title, thumbnail, channel, description)
# - All searches use strict safe search and Portuguese content preference
# - Excludes YouTube Shorts by filtering to medium duration (4-20 min)
# - Prioritizes recent videos (current year), falls back to all-time if none found
#
# Architecture:
# - Direct API calls from AgentCore (no Lambda proxy)
# - API key from environment variable (set by AgentCore runtime)
# - No boto3/SSM dependency (follows ElevenLabs pattern)
#
# OPTIMIZATION: Uses only standard library (no tenacity dependency)
# Simple retry loop replaces tenacity decorator for faster imports.
# =============================================================================

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional, Dict, List

# =============================================================================
# Configuration
# =============================================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# API endpoints
YOUTUBE_SEARCH_API = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_API = "https://www.googleapis.com/youtube/v3/videos"

# Search parameters
DEFAULT_MAX_RESULTS = 1
MAX_RESULTS_LIMIT = 5  # YouTube allows max 50, but we cap at 5 for performance
REGION_CODE = "BR"  # Brazil for Portuguese content
RELEVANCE_LANGUAGE = "pt"  # Portuguese language preference
SAFE_SEARCH = "strict"  # Educational content - keep it safe
VIDEO_DURATION = "medium"  # 4-20 min videos (first filter, not 100% effective)

# Duration filter (via videos.list API)
MIN_DURATION_SECONDS = 600  # 10 minutes minimum - short videos don't add value

# Limits
MAX_QUERIES_PER_BATCH = 4  # 4 * 100 = 400 quota units per batch

# =============================================================================
# API Client
# =============================================================================


def validate_api_key() -> None:
    """
    Validate YouTube API key is configured.

    Raises:
        ValueError: If API key not set
    """
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY environment variable not set")


# =============================================================================
# Duration Helpers (for Shorts filtering)
# =============================================================================


def _parse_iso8601_duration(duration: str) -> int:
    """
    Parse ISO 8601 duration format to seconds.

    YouTube returns durations in ISO 8601 format: PT1H2M30S
    - PT = Period Time marker
    - H = hours, M = minutes, S = seconds

    Examples:
        PT1M30S → 90 seconds
        PT5M → 300 seconds
        PT1H2M30S → 3750 seconds
        PT45S → 45 seconds (Short!)

    Args:
        duration: ISO 8601 duration string (e.g., "PT1M30S")

    Returns:
        Total duration in seconds (0 if parse fails)
    """
    if not duration:
        return 0

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        print(f"[YouTube] Failed to parse duration: {duration}")
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def _get_video_durations(video_ids: List[str]) -> Dict[str, int]:
    """
    Fetch video durations via YouTube videos.list API.

    This is the definitive way to detect Shorts:
    - Shorts are ≤60 seconds
    - This API costs only 1 quota unit (vs 100 for search)

    Args:
        video_ids: List of YouTube video IDs (max 50 per call)

    Returns:
        Dict mapping video_id → duration in seconds
        Videos not found will not be in the dict

    Raises:
        ConnectionError: If API request fails after retries
    """
    if not video_ids:
        return {}

    params = urllib.parse.urlencode({
        "part": "contentDetails",
        "id": ",".join(video_ids[:50]),  # API limit is 50
        "key": YOUTUBE_API_KEY,
    })
    url = f"{YOUTUBE_VIDEOS_API}?{params}"

    try:
        data = _make_youtube_request(url)
    except Exception as e:
        print(f"[YouTube] Failed to fetch video details: {e}")
        return {}

    durations = {}
    for item in data.get("items", []):
        video_id = item.get("id")
        content_details = item.get("contentDetails", {})
        duration_iso = content_details.get("duration", "")

        if video_id and duration_iso:
            durations[video_id] = _parse_iso8601_duration(duration_iso)

    print(f"[YouTube] Fetched durations for {len(durations)}/{len(video_ids)} videos")
    return durations


# =============================================================================
# Search Functions
# =============================================================================


def _make_youtube_request(url: str, max_retries: int = 3) -> dict:
    """
    Make HTTP request to YouTube API with simple retry logic.

    Uses exponential backoff: 2s, 4s, 8s wait between retries.

    Args:
        url: Full YouTube API URL with query parameters
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Parsed JSON response from YouTube API

    Raises:
        ValueError: If API key invalid or quota exceeded
        ConnectionError: If all retries fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/json"}
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            print(f"[YouTube] HTTP error (attempt {attempt + 1}): {e.code} - {e.reason}")
            if e.code == 403:
                raise ValueError("YouTube API quota exceeded or invalid API key")
            elif e.code == 400:
                raise ValueError(f"Invalid YouTube API request: {e.reason}")
            last_error = e
            # Don't retry HTTP errors other than 5xx
            if e.code < 500:
                raise

        except (urllib.error.URLError, TimeoutError) as e:
            print(f"[YouTube] Network error (attempt {attempt + 1}): {e}")
            last_error = e

        # Exponential backoff: 2s, 4s, 8s
        if attempt < max_retries - 1:
            wait_time = 2 ** (attempt + 1)
            print(f"[YouTube] Retrying in {wait_time}s...")
            time.sleep(wait_time)

    raise ConnectionError(f"Failed after {max_retries} attempts: {last_error}")


def _get_current_year_start() -> str:
    """
    Get RFC 3339 formatted datetime for the start of current year.

    Returns:
        ISO 8601 datetime string (e.g., "2025-01-01T00:00:00Z")
    """
    current_year = datetime.now().year
    return f"{current_year}-01-01T00:00:00Z"


def _is_short_video(title: str, description: str) -> bool:
    """
    Check if video is a YouTube Short based on title/description.

    Args:
        title: Video title
        description: Video description

    Returns:
        True if video appears to be a Short
    """
    text = f"{title} {description}".lower()
    # Check for common Short indicators
    return "#shorts" in text or "#short" in text or "| shorts" in text


def _execute_youtube_search(
    query: str,
    max_results: int,
    published_after: Optional[str] = None
) -> Optional[Dict]:
    """
    Execute a single YouTube search API call with Shorts filtering.

    Uses a two-step process for 100% accurate Shorts detection:
    1. search.list to find candidate videos (100 quota units)
    2. videos.list to get actual duration (1 quota unit)
    3. Filter out videos ≤60 seconds (definitively Shorts)

    Args:
        query: Cleaned search query
        max_results: Max results to return (we fetch more to filter Shorts)
        published_after: Optional RFC 3339 date filter (e.g., "2025-01-01T00:00:00Z")

    Returns:
        Video metadata dict or None if not found
    """
    # Fetch more results to have candidates after filtering Shorts
    # Increased from 5 to 10 for better filtering margin
    fetch_count = min(max_results + 9, 10)

    # Build base params
    params_dict = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": fetch_count,
        "regionCode": REGION_CODE,
        "relevanceLanguage": RELEVANCE_LANGUAGE,
        "safeSearch": SAFE_SEARCH,
        "videoDuration": VIDEO_DURATION,  # First filter (not 100% effective)
        "key": YOUTUBE_API_KEY,
    }

    # Add date filter if specified
    if published_after:
        params_dict["publishedAfter"] = published_after

    params = urllib.parse.urlencode(params_dict)
    url = f"{YOUTUBE_SEARCH_API}?{params}"

    data = _make_youtube_request(url)
    items = data.get("items", [])

    if not items:
        return None

    # Collect video IDs for duration check
    video_ids = []
    video_data_map = {}  # video_id → (snippet, item)

    for item in items:
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            video_ids.append(video_id)
            video_data_map[video_id] = item.get("snippet", {})

    if not video_ids:
        return None

    # Get actual durations via videos.list API (1 quota unit)
    durations = _get_video_durations(video_ids)

    # Find first non-Short video (≤60s = Short)
    for video_id in video_ids:
        snippet = video_data_map.get(video_id, {})
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        duration = durations.get(video_id, 0)

        # Filter out short videos (< 10 minutes) - they don't add educational value
        if duration > 0 and duration < MIN_DURATION_SECONDS:
            mins = duration // 60
            print(f"[YouTube] Skipping short video ({mins}min): {title[:40]}...")
            continue

        # Backup: Skip Shorts based on title/description (for videos where duration fetch failed)
        if duration == 0 and _is_short_video(title, description):
            print(f"[YouTube] Skipping Short (by title): {title[:40]}...")
            continue

        # Get best available thumbnail
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("medium", {}).get("url") or
            thumbnails.get("default", {}).get("url") or
            f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
        )

        duration_str = f" ({duration // 60}min)" if duration > 0 else ""
        print(f"[YouTube] Selected video{duration_str}: {title[:50]}...")

        return {
            "videoId": video_id,
            "title": title or query,
            "channelTitle": snippet.get("channelTitle", "YouTube"),
            "thumbnailUrl": thumbnail_url,
            "description": (description[:150] or "").strip(),
            "searchQuery": query,
        }

    # All results were Shorts
    print(f"[YouTube] All {len(items)} results were Shorts (filtered by duration)")
    return None


def search_youtube_video(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS
) -> Optional[Dict]:
    """
    Search YouTube for videos matching the query.

    Uses YouTube Data API v3 search.list endpoint.
    Strategy: First searches for videos from current year, then falls back
    to all-time search if no recent videos found.

    Costs 100-200 quota units per call (100 per search attempt).

    Args:
        query: Search query string (in Portuguese for best results)
        max_results: Maximum number of results to return (1-5)

    Returns:
        Dict with video metadata if found:
        {
            "videoId": "abc123",
            "title": "Video Title",
            "channelTitle": "Channel Name",
            "thumbnailUrl": "https://i.ytimg.com/vi/abc123/mqdefault.jpg",
            "description": "Video description...",
            "searchQuery": "original search query"
        }
        Returns None if no results or error.

    Raises:
        ValueError: If API key not configured or query invalid
        ConnectionError: If YouTube API is unreachable
    """
    # Validate inputs
    validate_api_key()

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    cleaned_query = query.strip()

    try:
        # First attempt: Search for videos from current year
        current_year_start = _get_current_year_start()
        print(f"[YouTube] Searching for recent videos (since {current_year_start[:4]})...")

        result = _execute_youtube_search(cleaned_query, max_results, current_year_start)

        if result:
            print(f"[YouTube] Found recent video: {result['title'][:50]}...")
            return result

        # Fallback: Search without date filter
        print(f"[YouTube] No recent videos, searching all-time...")
        result = _execute_youtube_search(cleaned_query, max_results, None)

        if result:
            print(f"[YouTube] Found video (all-time): {result['title'][:50]}...")
            return result

        print(f"[YouTube] No results for query: {cleaned_query[:50]}...")
        return None

    except json.JSONDecodeError as e:
        print(f"[YouTube] JSON decode error: {e}")
        raise ValueError(f"Invalid JSON response from YouTube API: {e}")

    except Exception as e:
        print(f"[YouTube] Unexpected error: {e}")
        raise


def search_multiple_videos(queries: List[str]) -> List[Dict]:
    """
    Search YouTube for multiple queries.

    Processes queries sequentially (no parallel requests to respect rate limits).
    Costs 100 quota units per successful query.

    Args:
        queries: List of search queries (max 4 will be processed)

    Returns:
        List of video metadata dicts for successful searches.
        Empty list if all searches fail.

    Raises:
        ValueError: If API key not configured
    """
    validate_api_key()

    results = []

    # Limit to MAX_QUERIES_PER_BATCH to manage API quota
    for query in queries[:MAX_QUERIES_PER_BATCH]:
        if not query or not query.strip():
            continue

        try:
            video = search_youtube_video(query.strip())
            if video:
                results.append(video)
        except Exception as e:
            # Log error but continue processing remaining queries
            print(f"[YouTube] Failed to search '{query[:30]}...': {e}")
            continue

    print(f"[YouTube] Batch search complete: {len(results)}/{len(queries[:MAX_QUERIES_PER_BATCH])} videos found")
    return results


# =============================================================================
# Utility Functions
# =============================================================================


def get_quota_cost(num_queries: int) -> int:
    """
    Calculate quota cost for a number of search queries.

    Cost per search: 101 units (100 for search.list + 1 for videos.list)

    Args:
        num_queries: Number of search queries

    Returns:
        Total quota units required
    """
    return num_queries * 101  # search.list (100) + videos.list (1)


def format_video_url(video_id: str) -> str:
    """
    Format a YouTube video URL from video ID.

    Args:
        video_id: YouTube video ID

    Returns:
        Full YouTube video URL
    """
    return f"https://www.youtube.com/watch?v={video_id}"


def format_embed_url(video_id: str) -> str:
    """
    Format a YouTube embed URL from video ID.

    Args:
        video_id: YouTube video ID

    Returns:
        YouTube embed URL for iframe
    """
    return f"https://www.youtube.com/embed/{video_id}"


# =============================================================================
# Quota Management Reference
# =============================================================================
#
# YouTube Data API v3 Quota:
# - Daily quota: 10,000 units (free tier)
# - search.list cost: 100 units per call
# - videos.list cost: 1 unit per call (for duration check)
# - Total per search: 101 units
# - Max daily searches: ~99 calls
#
# Our Usage Pattern:
# - ~4 searches per episode generation (404 units)
# - ~24 episodes per day max (theoretical limit)
#
# Duration Filtering Strategy:
# - search.list returns candidates with videoDuration=medium (4-20 min initial filter)
# - videos.list fetches actual duration for each video (1 quota unit)
# - Videos < 10 minutes are filtered out (short videos don't add educational value)
# - This ensures only substantive, in-depth content is recommended
#
# Best Practices:
# - Batch searches when possible
# - Cache results to avoid duplicate searches
# - Use specific queries to get relevant results on first try
# - Monitor quota usage in Google Cloud Console
#
# Error Handling:
# - 403 Forbidden: Quota exceeded or invalid key
# - 400 Bad Request: Invalid parameters
# - 404 Not Found: Invalid video ID (not applicable for search)
#
# Reference:
# - https://developers.google.com/youtube/v3/docs/search/list
# - https://developers.google.com/youtube/v3/determine_quota_cost
# =============================================================================
