# =============================================================================
# Tavily Gateway Adapter for Equipment Enrichment
# =============================================================================
# MCP client wrapper for Tavily tools via AgentCore Gateway.
#
# Per CLAUDE.md MCP ACCESS POLICY:
# > ALL MCP tools and servers MUST be accessed ONLY via AWS Bedrock AgentCore Gateway.
#
# Architecture:
#     EnrichmentAgent -> TavilyGatewayAdapter -> MCPGatewayClient (SigV4) ->
#     AgentCore Gateway -> Tavily API (OpenAPI Target)
#
# Tool Naming Convention (per AWS docs):
#     Format: {TargetName}___{ToolName} (THREE underscores)
#     Example: TavilySearchMCP___tavily-search
#
# Available Tools:
#     - tavily-search: AI-optimized web search
#     - tavily-extract: Content extraction from URLs
#     - tavily-crawl: Systematic website crawling
#     - tavily-map: Site structure mapping
#
# Reference:
#     - PRD: product-development/current-feature/PRD-tavily-enrichment.md
#     - Tavily MCP: https://github.com/tavily-ai/tavily-mcp
#     - Gateway: terraform/main/agentcore_gateway.tf
#
# Author: Faiston NEXO Team
# Date: January 2026
# =============================================================================

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from tools.mcp_gateway_client import MCPGatewayClient, MCPGatewayClientFactory

logger = logging.getLogger(__name__)


# =============================================================================
# Types and Enums
# =============================================================================


class SearchDepth(str, Enum):
    """Search depth for Tavily queries."""
    BASIC = "basic"
    ADVANCED = "advanced"


class SearchTopic(str, Enum):
    """Topic type for Tavily search."""
    GENERAL = "general"
    NEWS = "news"


class TimeRange(str, Enum):
    """Time range filter for search results."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class ExtractFormat(str, Enum):
    """Output format for content extraction."""
    MARKDOWN = "markdown"
    TEXT = "text"


@dataclass
class SearchResult:
    """A single search result from Tavily."""
    url: str
    title: str
    content: str
    raw_content: Optional[str] = None
    favicon: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class ExtractResult:
    """Content extracted from a URL."""
    url: str
    title: str
    content: str
    raw_content: Optional[str] = None
    favicon: Optional[str] = None
    images: List[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    """Result from website crawl."""
    base_url: str
    pages_crawled: int
    results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MapResult:
    """Site map structure from Tavily map."""
    base_url: str
    urls: List[str] = field(default_factory=list)
    depth_reached: int = 0


# =============================================================================
# Tavily Gateway Adapter
# =============================================================================


class TavilyGatewayAdapter:
    """
    Adapter for Tavily tools via AgentCore Gateway.

    This adapter translates high-level search/extract/crawl operations
    into MCP tool invocations via the Gateway. It handles:
    - Tool name prefixing with target name
    - Argument serialization
    - Response parsing into typed dataclasses
    - Error handling with sensible defaults

    Note: All methods are SYNCHRONOUS. The MCPGatewayClient uses SigV4
    signing and the requests library for HTTP calls.

    Attributes:
        TARGET_PREFIX: MCP target name for Tavily tools
        _client: MCPGatewayClient instance for Gateway communication

    Example:
        ```python
        adapter = TavilyGatewayAdapter.create_from_env()

        # Search for equipment documentation
        results = adapter.search(
            query="Cisco C9200-24P datasheet PDF",
            search_depth=SearchDepth.ADVANCED,
            include_domains=["cisco.com"],
            max_results=5,
        )

        # Extract content from official page
        extracted = adapter.extract(
            urls=["https://cisco.com/c9200-datasheet"],
            extract_depth="advanced",
            format=ExtractFormat.MARKDOWN,
        )
        ```
    """

    TARGET_PREFIX = "TavilySearchMCP"

    def __init__(self, mcp_client: MCPGatewayClient):
        """
        Initialize Tavily Gateway Adapter.

        Args:
            mcp_client: Configured MCPGatewayClient for Gateway communication
        """
        self._client = mcp_client
        logger.info("[TavilyGatewayAdapter] Initialized with Gateway MCP client")

    def _tool_name(self, tool: str) -> str:
        """
        Build full tool name with target prefix.

        Per AWS MCP Gateway convention, tools are prefixed with:
        {TargetName}___{ToolName} (THREE underscores)

        Note: Tavily tools use hyphens (tavily-search), not underscores.

        Args:
            tool: Base tool name (e.g., "tavily-search")

        Returns:
            Full tool name (e.g., "TavilySearchMCP___tavily-search")
        """
        return f"{self.TARGET_PREFIX}___{tool}"

    def _clean_none_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove None values from dictionary for cleaner MCP calls.

        Args:
            data: Dictionary potentially containing None values

        Returns:
            Dictionary with None values removed
        """
        return {k: v for k, v in data.items() if v is not None}

    # =========================================================================
    # tavily-search: AI-Optimized Web Search
    # =========================================================================

    def search(
        self,
        query: str,
        search_depth: SearchDepth = SearchDepth.BASIC,
        topic: SearchTopic = SearchTopic.GENERAL,
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_images: bool = False,
        include_raw_content: bool = False,
        time_range: Optional[TimeRange] = None,
        days: Optional[int] = None,
        country: Optional[str] = None,
        timeout: int = 60,
    ) -> List[SearchResult]:
        """
        Search the web using Tavily's AI-optimized search engine.

        Tavily search is optimized for AI agents and provides:
        - Relevant, high-quality results
        - Domain filtering for official sources
        - Raw content extraction for RAG pipelines
        - Image extraction for documentation

        Args:
            query: Search query (e.g., "Cisco C9200-24P specifications PDF")
            search_depth: BASIC (fast) or ADVANCED (comprehensive)
            topic: GENERAL or NEWS
            max_results: Maximum results to return (default 5)
            include_domains: Only include results from these domains
            exclude_domains: Exclude results from these domains
            include_images: Include images in results
            include_raw_content: Include full page content
            time_range: Filter by time (day, week, month, year)
            days: Number of days for news search
            country: Country for localized results
            timeout: Request timeout in seconds

        Returns:
            List of SearchResult objects with url, title, content

        Example:
            ```python
            # Search for official Cisco documentation
            results = adapter.search(
                query="Cisco C9200-24P datasheet",
                search_depth=SearchDepth.ADVANCED,
                include_domains=["cisco.com"],
                include_raw_content=True,
            )
            ```
        """
        logger.info(f"[TavilyGatewayAdapter] search: query='{query[:50]}...'")

        arguments = self._clean_none_values({
            "query": query,
            "search_depth": search_depth.value,
            "topic": topic.value,
            "max_results": max_results,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
            "include_images": include_images,
            "include_raw_content": include_raw_content,
            "time_range": time_range.value if time_range else None,
            "days": days,
            "country": country,
        })

        try:
            result = self._client.call_tool(
                tool_name=self._tool_name("tavily-search"),
                arguments=arguments,
                timeout=timeout,
            )

            # Parse response into SearchResult objects
            results = self._parse_search_results(result)
            logger.info(f"[TavilyGatewayAdapter] search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[TavilyGatewayAdapter] search failed: {e}")
            return []

    def _parse_search_results(self, response: Dict[str, Any]) -> List[SearchResult]:
        """Parse Tavily search response into SearchResult objects."""
        results = []

        # Handle different response structures
        items = response.get("results", response.get("items", []))
        if not isinstance(items, list):
            items = [response] if "url" in response else []

        for item in items:
            try:
                results.append(SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    content=item.get("content", item.get("snippet", "")),
                    raw_content=item.get("raw_content"),
                    favicon=item.get("favicon"),
                    relevance_score=float(item.get("score", item.get("relevance_score", 0.5))),
                ))
            except Exception as e:
                logger.warning(f"[TavilyGatewayAdapter] Failed to parse result: {e}")

        return results

    # =========================================================================
    # tavily-extract: Content Extraction from URLs
    # =========================================================================

    def extract(
        self,
        urls: List[str],
        extract_depth: str = "basic",
        format: ExtractFormat = ExtractFormat.MARKDOWN,
        include_images: bool = False,
        include_favicon: bool = False,
        timeout: int = 120,
    ) -> List[ExtractResult]:
        """
        Extract and process content from specified URLs.

        Useful for:
        - Extracting datasheet content from manufacturer sites
        - Processing documentation pages into structured text
        - Batch extraction from multiple URLs

        Args:
            urls: List of URLs to extract content from
            extract_depth: "basic" or "advanced"
            format: Output format (MARKDOWN or TEXT)
            include_images: Extract images from pages
            include_favicon: Include favicon URLs
            timeout: Request timeout in seconds

        Returns:
            List of ExtractResult objects with extracted content

        Example:
            ```python
            # Extract content from Cisco datasheet
            extracted = adapter.extract(
                urls=["https://cisco.com/c/dam/en/us/products/collateral/switches/catalyst-9200-series-switches/nb-06-cat9200-ser-data-sheet-cte-en.pdf"],
                extract_depth="advanced",
                format=ExtractFormat.MARKDOWN,
            )
            ```
        """
        logger.info(f"[TavilyGatewayAdapter] extract: {len(urls)} URLs")

        arguments = self._clean_none_values({
            "urls": urls,
            "extract_depth": extract_depth,
            "format": format.value,
            "include_images": include_images,
            "include_favicon": include_favicon,
        })

        try:
            result = self._client.call_tool(
                tool_name=self._tool_name("tavily-extract"),
                arguments=arguments,
                timeout=timeout,
            )

            # Parse response into ExtractResult objects
            results = self._parse_extract_results(result)
            logger.info(f"[TavilyGatewayAdapter] extract returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[TavilyGatewayAdapter] extract failed: {e}")
            return []

    def _parse_extract_results(self, response: Dict[str, Any]) -> List[ExtractResult]:
        """Parse Tavily extract response into ExtractResult objects."""
        results = []

        items = response.get("results", [])
        if not isinstance(items, list):
            items = [response] if "url" in response else []

        for item in items:
            try:
                images = item.get("images", [])
                if isinstance(images, list):
                    image_urls = [
                        img.get("url", img) if isinstance(img, dict) else img
                        for img in images
                    ]
                else:
                    image_urls = []

                results.append(ExtractResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    raw_content=item.get("raw_content"),
                    favicon=item.get("favicon"),
                    images=image_urls,
                ))
            except Exception as e:
                logger.warning(f"[TavilyGatewayAdapter] Failed to parse extract result: {e}")

        return results

    # =========================================================================
    # tavily-crawl: Systematic Website Crawling
    # =========================================================================

    def crawl(
        self,
        url: str,
        max_depth: int = 2,
        max_breadth: int = 10,
        limit: int = 30,
        instructions: Optional[str] = None,
        select_paths: Optional[List[str]] = None,
        select_domains: Optional[List[str]] = None,
        allow_external: bool = False,
        extract_depth: str = "basic",
        format: ExtractFormat = ExtractFormat.MARKDOWN,
        include_favicon: bool = False,
        timeout: int = 180,
    ) -> CrawlResult:
        """
        Systematically crawl a website to collect documentation.

        Useful for:
        - Crawling vendor documentation portals
        - Collecting all product pages from a manufacturer
        - Building comprehensive equipment knowledge bases

        Args:
            url: Starting URL for crawl
            max_depth: How deep to follow links (default 2)
            max_breadth: Maximum links per page (default 10)
            limit: Maximum total pages to crawl (default 30)
            instructions: Natural language crawl instructions
            select_paths: Regex patterns for paths to include
            select_domains: Regex patterns for domains to include
            allow_external: Follow links to external domains
            extract_depth: Content extraction depth
            format: Output format for content
            include_favicon: Include favicon URLs
            timeout: Request timeout in seconds

        Returns:
            CrawlResult with list of crawled page data

        Example:
            ```python
            # Crawl Cisco product documentation
            crawl_result = adapter.crawl(
                url="https://cisco.com/c/en/us/products/switches/catalyst-9200-series-switches/",
                max_depth=3,
                limit=50,
                instructions="Collect all datasheets and installation guides",
                select_paths=["/c/dam/.*\\.pdf", "/c/en/us/products/.*"],
            )
            ```
        """
        logger.info(f"[TavilyGatewayAdapter] crawl: url={url}, depth={max_depth}, limit={limit}")

        arguments = self._clean_none_values({
            "url": url,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "limit": limit,
            "instructions": instructions,
            "select_paths": select_paths,
            "select_domains": select_domains,
            "allow_external": allow_external,
            "extract_depth": extract_depth,
            "format": format.value,
            "include_favicon": include_favicon,
        })

        try:
            result = self._client.call_tool(
                tool_name=self._tool_name("tavily-crawl"),
                arguments=arguments,
                timeout=timeout,
            )

            # Parse response into CrawlResult
            crawl_result = self._parse_crawl_result(url, result)
            logger.info(
                f"[TavilyGatewayAdapter] crawl completed: "
                f"{crawl_result.pages_crawled} pages"
            )
            return crawl_result

        except Exception as e:
            logger.error(f"[TavilyGatewayAdapter] crawl failed: {e}")
            return CrawlResult(base_url=url, pages_crawled=0, results=[])

    def _parse_crawl_result(self, base_url: str, response: Dict[str, Any]) -> CrawlResult:
        """Parse Tavily crawl response into CrawlResult."""
        results = response.get("results", [])
        if not isinstance(results, list):
            results = []

        return CrawlResult(
            base_url=base_url,
            pages_crawled=len(results),
            results=results,
        )

    # =========================================================================
    # tavily-map: Site Structure Mapping
    # =========================================================================

    def map(
        self,
        url: str,
        max_depth: int = 2,
        max_breadth: int = 20,
        limit: int = 50,
        instructions: Optional[str] = None,
        select_paths: Optional[List[str]] = None,
        select_domains: Optional[List[str]] = None,
        allow_external: bool = False,
        timeout: int = 120,
    ) -> MapResult:
        """
        Generate a site map to understand website structure.

        Useful for:
        - Discovering all documentation URLs on a vendor site
        - Planning targeted crawls
        - Understanding content organization

        Args:
            url: Starting URL for mapping
            max_depth: How deep to explore (default 2)
            max_breadth: Maximum links per page (default 20)
            limit: Maximum total URLs to discover (default 50)
            instructions: Natural language mapping instructions
            select_paths: Regex patterns for paths to include
            select_domains: Regex patterns for domains to include
            allow_external: Include external domain links
            timeout: Request timeout in seconds

        Returns:
            MapResult with list of discovered URLs

        Example:
            ```python
            # Map Cisco documentation structure
            site_map = adapter.map(
                url="https://cisco.com/c/en/us/support/",
                max_depth=3,
                limit=100,
                instructions="Find all product support pages",
            )
            print(f"Found {len(site_map.urls)} URLs")
            ```
        """
        logger.info(f"[TavilyGatewayAdapter] map: url={url}, depth={max_depth}, limit={limit}")

        arguments = self._clean_none_values({
            "url": url,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "limit": limit,
            "instructions": instructions,
            "select_paths": select_paths,
            "select_domains": select_domains,
            "allow_external": allow_external,
        })

        try:
            result = self._client.call_tool(
                tool_name=self._tool_name("tavily-map"),
                arguments=arguments,
                timeout=timeout,
            )

            # Parse response into MapResult
            map_result = self._parse_map_result(url, result)
            logger.info(
                f"[TavilyGatewayAdapter] map completed: "
                f"{len(map_result.urls)} URLs discovered"
            )
            return map_result

        except Exception as e:
            logger.error(f"[TavilyGatewayAdapter] map failed: {e}")
            return MapResult(base_url=url, urls=[], depth_reached=0)

    def _parse_map_result(self, base_url: str, response: Dict[str, Any]) -> MapResult:
        """Parse Tavily map response into MapResult."""
        urls = response.get("urls", response.get("results", []))
        if not isinstance(urls, list):
            urls = []

        # Extract URL strings if nested
        url_list = []
        for item in urls:
            if isinstance(item, str):
                url_list.append(item)
            elif isinstance(item, dict) and "url" in item:
                url_list.append(item["url"])

        return MapResult(
            base_url=base_url,
            urls=url_list,
            depth_reached=response.get("depth_reached", 0),
        )

    # =========================================================================
    # High-Level Equipment Research Methods
    # =========================================================================

    def research_equipment(
        self,
        part_number: str,
        manufacturer: Optional[str] = None,
        search_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive equipment research using multiple Tavily tools.

        Combines search, extract, and optionally crawl to gather
        complete documentation for a piece of equipment.

        Args:
            part_number: Equipment part number (e.g., "C9200-24P")
            manufacturer: Manufacturer name for domain filtering
            search_types: Types of docs to search for (default: all)

        Returns:
            Dictionary with:
            - part_number: str
            - manufacturer: str
            - datasheet: SearchResult or None
            - manual: SearchResult or None
            - specifications: Dict[str, Any]
            - sources: List[str] (all URLs used)

        Example:
            ```python
            research = adapter.research_equipment(
                part_number="C9200-24P",
                manufacturer="Cisco",
            )
            print(f"Found datasheet: {research['datasheet'].url}")
            ```
        """
        logger.info(
            f"[TavilyGatewayAdapter] research_equipment: "
            f"part_number={part_number}, manufacturer={manufacturer}"
        )

        search_types = search_types or ["datasheet", "manual", "specifications"]
        sources = []
        results = {
            "part_number": part_number,
            "manufacturer": manufacturer or "Unknown",
            "datasheet": None,
            "manual": None,
            "specifications": {},
            "sources": [],
        }

        # Build domain filters
        include_domains = None
        if manufacturer:
            # Common manufacturer domain patterns
            manufacturer_domains = {
                "cisco": ["cisco.com"],
                "dell": ["dell.com"],
                "hp": ["hp.com", "hpe.com"],
                "lenovo": ["lenovo.com"],
                "ibm": ["ibm.com"],
                "juniper": ["juniper.net"],
                "arista": ["arista.com"],
                "netgear": ["netgear.com"],
                "ubiquiti": ["ui.com", "ubnt.com"],
            }
            include_domains = manufacturer_domains.get(
                manufacturer.lower(), [f"{manufacturer.lower()}.com"]
            )

        # Search for each document type
        for doc_type in search_types:
            query = f"{part_number} {doc_type}"
            if manufacturer:
                query = f"{manufacturer} {query}"

            search_results = self.search(
                query=query,
                search_depth=SearchDepth.ADVANCED,
                include_domains=include_domains,
                max_results=3,
                include_raw_content=True,
            )

            if search_results:
                best_result = search_results[0]
                sources.append(best_result.url)

                if doc_type == "datasheet":
                    results["datasheet"] = best_result
                elif doc_type == "manual":
                    results["manual"] = best_result
                elif doc_type == "specifications":
                    results["specifications"] = {
                        "url": best_result.url,
                        "content": best_result.content,
                        "raw_content": best_result.raw_content,
                    }

        results["sources"] = list(set(sources))
        logger.info(
            f"[TavilyGatewayAdapter] research_equipment completed: "
            f"{len(results['sources'])} sources found"
        )

        return results


# =============================================================================
# Factory
# =============================================================================


class TavilyGatewayAdapterFactory:
    """
    Factory for creating TavilyGatewayAdapter instances.

    Handles the setup of MCPGatewayClient and adapter creation,
    abstracting the complexity from agent code.

    Uses IAM-based authentication (SigV4) - no tokens required.
    The AgentCore Runtime's execution role provides credentials.
    """

    @staticmethod
    def create_from_env() -> TavilyGatewayAdapter:
        """
        Create adapter from environment variables.

        Uses IAM SigV4 authentication (not Bearer tokens).
        Credentials come from AgentCore Runtime's execution role.

        Environment Variables:
            AGENTCORE_GATEWAY_URL: Full MCP endpoint URL
            AGENTCORE_GATEWAY_ID: Gateway ID (alternative to full URL)
            AWS_REGION: AWS region for URL construction and SigV4 signing

        Returns:
            Configured TavilyGatewayAdapter

        Raises:
            ValueError: If required environment variables are missing
        """
        client = MCPGatewayClientFactory.create_from_env()
        logger.info("[TavilyGatewayAdapterFactory] Created adapter with IAM auth (SigV4)")

        return TavilyGatewayAdapter(client)

    @staticmethod
    def create_with_url(
        gateway_url: str,
        region: str = "us-east-2"
    ) -> TavilyGatewayAdapter:
        """
        Create adapter with explicit Gateway URL.

        Uses IAM SigV4 authentication (not Bearer tokens).

        Args:
            gateway_url: Full Gateway MCP endpoint URL
            region: AWS region for SigV4 signing

        Returns:
            Configured TavilyGatewayAdapter
        """
        client = MCPGatewayClient(gateway_url=gateway_url, region=region)
        logger.info(f"[TavilyGatewayAdapterFactory] Created adapter for {gateway_url}")

        return TavilyGatewayAdapter(client)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Types
    "SearchDepth",
    "SearchTopic",
    "TimeRange",
    "ExtractFormat",
    "SearchResult",
    "ExtractResult",
    "CrawlResult",
    "MapResult",
    # Adapter
    "TavilyGatewayAdapter",
    "TavilyGatewayAdapterFactory",
]
