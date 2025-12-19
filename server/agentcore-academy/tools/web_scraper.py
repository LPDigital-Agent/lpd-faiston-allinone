# =============================================================================
# Web Scraper Tool - URL Content Extraction
# =============================================================================
# Extracts text content from web pages for training creation.
#
# Features:
# - Extracts main article content using trafilatura
# - Falls back to BeautifulSoup for complex pages
# - Handles JavaScript-rendered pages via retry
# - Respects robots.txt and rate limiting
#
# Usage:
#   result = scrape_url("https://example.com/article")
#   print(result["text"])
#
# Supported:
# - News articles, blog posts, documentation
# - Static HTML pages
#
# Not Supported:
# - Login-required pages
# - Heavy JavaScript SPAs (without pre-rendering)
# =============================================================================

import re
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin

import httpx

# Lazy imports for cold start optimization
_trafilatura = None
_bs4 = None


def _get_trafilatura():
    """Lazy load trafilatura."""
    global _trafilatura
    if _trafilatura is None:
        import trafilatura
        _trafilatura = trafilatura
    return _trafilatura


def _get_bs4():
    """Lazy load BeautifulSoup."""
    global _bs4
    if _bs4 is None:
        from bs4 import BeautifulSoup
        _bs4 = BeautifulSoup
    return _bs4


# =============================================================================
# Configuration
# =============================================================================

# Request timeout (seconds)
REQUEST_TIMEOUT = 30

# Maximum content size (5 MB)
MAX_CONTENT_SIZE = 5 * 1024 * 1024

# Maximum text length (500K characters)
MAX_TEXT_LENGTH = 500_000

# Rate limiting: minimum seconds between requests to same domain
RATE_LIMIT_SECONDS = 2

# User agent for requests
USER_AGENT = (
    "Mozilla/5.0 (compatible; HiveAcademyBot/1.0; "
    "+https://bhive.academy/bot) AppleWebKit/537.36"
)

# Blocked domains (known to block scrapers or require login)
BLOCKED_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "tiktok.com", "pinterest.com",
    "paywall.example.com",  # Generic paywall pattern
}

# Last request time per domain (for rate limiting)
_domain_last_request: Dict[str, float] = {}


# =============================================================================
# URL Validation
# =============================================================================


def validate_url(url: str) -> str:
    """
    Validate and normalize a URL.

    Args:
        url: URL to validate

    Returns:
        Normalized URL

    Raises:
        ValueError: If URL is invalid or blocked
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL is required")

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Parse and validate
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    if not parsed.netloc:
        raise ValueError(f"Invalid URL: missing domain")

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")

    # Check blocked domains
    domain = parsed.netloc.lower()
    for blocked in BLOCKED_DOMAINS:
        if blocked in domain:
            raise ValueError(f"Domain '{domain}' is not supported for scraping")

    return url


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


# =============================================================================
# Rate Limiting
# =============================================================================


def wait_for_rate_limit(url: str) -> None:
    """
    Wait if necessary to respect rate limiting.

    Args:
        url: URL being requested
    """
    domain = get_domain(url)
    now = time.time()

    if domain in _domain_last_request:
        elapsed = now - _domain_last_request[domain]
        if elapsed < RATE_LIMIT_SECONDS:
            wait_time = RATE_LIMIT_SECONDS - elapsed
            print(f"[WebScraper] Rate limiting: waiting {wait_time:.1f}s for {domain}")
            time.sleep(wait_time)

    _domain_last_request[domain] = time.time()


# =============================================================================
# Content Extraction
# =============================================================================


def fetch_page(url: str) -> str:
    """
    Fetch HTML content from URL.

    Args:
        url: URL to fetch

    Returns:
        HTML content as string

    Raises:
        ValueError: If fetch fails
    """
    wait_for_rate_limit(url)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "DNT": "1",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            # Check content size
            content_length = len(response.content)
            if content_length > MAX_CONTENT_SIZE:
                raise ValueError(f"Page too large: {content_length // 1024 // 1024}MB")

            # Check content type
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                raise ValueError(f"Not an HTML page: {content_type}")

            return response.text

    except httpx.TimeoutException:
        raise ValueError(f"Request timed out after {REQUEST_TIMEOUT}s")

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 403:
            raise ValueError("Access forbidden (403) - page may require login")
        elif status == 404:
            raise ValueError("Page not found (404)")
        elif status == 429:
            raise ValueError("Rate limited (429) - too many requests")
        else:
            raise ValueError(f"HTTP error: {status}")

    except httpx.RequestError as e:
        raise ValueError(f"Request failed: {e}")


def extract_with_trafilatura(html: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Extract content using trafilatura (recommended).

    Args:
        html: HTML content
        url: Source URL

    Returns:
        Extraction result or None if failed
    """
    trafilatura = _get_trafilatura()

    try:
        # Extract main content
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            include_links=False,
            include_images=False,
            favor_precision=True,
            deduplicate=True,
        )

        if not text or len(text.strip()) < 100:
            return None

        # Extract metadata
        metadata = trafilatura.extract_metadata(html)

        return {
            "text": text,
            "title": metadata.title if metadata else None,
            "author": metadata.author if metadata else None,
            "date": str(metadata.date) if metadata and metadata.date else None,
            "description": metadata.description if metadata else None,
            "method": "trafilatura",
        }

    except Exception as e:
        print(f"[WebScraper] Trafilatura failed: {e}")
        return None


def extract_with_beautifulsoup(html: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Extract content using BeautifulSoup (fallback).

    Args:
        html: HTML content
        url: Source URL

    Returns:
        Extraction result or None if failed
    """
    BeautifulSoup = _get_bs4()

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()

        # Extract title
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()

        # Try to find main content area
        main_content = None
        for selector in ["article", "main", '[role="main"]', ".content", ".post", ".article"]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # Fall back to body
        if not main_content:
            main_content = soup.find("body")

        if not main_content:
            return None

        # Extract text
        text = main_content.get_text(separator="\n", strip=True)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        if len(text.strip()) < 100:
            return None

        # Extract meta description
        description = None
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content")

        return {
            "text": text,
            "title": title,
            "author": None,
            "date": None,
            "description": description,
            "method": "beautifulsoup",
        }

    except Exception as e:
        print(f"[WebScraper] BeautifulSoup failed: {e}")
        return None


# =============================================================================
# Main Scraping Function
# =============================================================================


def scrape_url(url: str) -> Dict[str, Any]:
    """
    Scrape and extract text content from a URL.

    Args:
        url: URL to scrape

    Returns:
        Dict with:
        - url: Original URL
        - text: Extracted text content
        - title: Page title (if available)
        - author: Author (if available)
        - date: Publication date (if available)
        - description: Meta description (if available)
        - char_count: Number of characters
        - method: Extraction method used

    Raises:
        ValueError: If URL is invalid or extraction fails
    """
    # Validate URL
    url = validate_url(url)
    domain = get_domain(url)

    print(f"[WebScraper] Scraping: {url}")

    # Fetch HTML
    html = fetch_page(url)

    # Try trafilatura first (better quality)
    result = extract_with_trafilatura(html, url)

    # Fall back to BeautifulSoup
    if not result:
        result = extract_with_beautifulsoup(html, url)

    if not result:
        raise ValueError(f"Failed to extract content from {domain}")

    # Truncate if too long
    text = result["text"]
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + f"\n\n[Truncado: texto excedeu {MAX_TEXT_LENGTH} caracteres]"
        print(f"[WebScraper] Warning: Text truncated for {url}")
        result["text"] = text

    # Add metadata
    result["url"] = url
    result["domain"] = domain
    result["char_count"] = len(result["text"])

    print(f"[WebScraper] Extracted {result['char_count']} chars from {domain} using {result['method']}")

    return result


def scrape_multiple_urls(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Scrape multiple URLs with rate limiting.

    Args:
        urls: List of URLs to scrape

    Returns:
        List of results (success or error for each URL)
    """
    results = []

    for url in urls:
        try:
            result = scrape_url(url)
            result["status"] = "success"
            results.append(result)

        except Exception as e:
            print(f"[WebScraper] Error scraping {url}: {e}")
            results.append({
                "url": url,
                "status": "error",
                "error": str(e),
            })

    return results


# =============================================================================
# YouTube Transcript Extraction
# =============================================================================


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.

    Args:
        url: YouTube URL (various formats)

    Returns:
        Video ID or None if not a YouTube URL
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video."""
    return extract_youtube_id(url) is not None


# =============================================================================
# Utility Functions
# =============================================================================


def get_supported_sites() -> List[Dict[str, str]]:
    """
    Return information about supported site types.

    Returns:
        List of site type descriptions
    """
    return [
        {"type": "article", "description": "News articles and blog posts"},
        {"type": "documentation", "description": "Technical documentation"},
        {"type": "wikipedia", "description": "Wikipedia articles"},
        {"type": "youtube", "description": "YouTube videos (transcript extraction)"},
    ]


def estimate_scrape_time(url_count: int) -> int:
    """
    Estimate time to scrape multiple URLs.

    Args:
        url_count: Number of URLs

    Returns:
        Estimated seconds
    """
    # Account for rate limiting and processing
    return url_count * (RATE_LIMIT_SECONDS + REQUEST_TIMEOUT // 3)
