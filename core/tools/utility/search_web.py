"""
Web Search tool - Search the internet for real-time information.

Provides AI agents with real-time internet access via DuckDuckGo search.
Returns top 3 search results with snippets. Supports caching and source filtering.
"""

from typing import Dict, Any, Optional
from core.tools.base import Tool
from core.tools.utility.search_cache import get_search_cache


class SearchWebTool(Tool):
    """Tool for searching the internet for real-time information."""

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return (
            "Search the internet for real-time information, current events, facts, "
            "news, or any information that requires up-to-date knowledge. Use this "
            "when you need to look up something beyond your training data or when "
            "the user asks about recent events, current news, or real-time information. "
            "Optionally filter results by domain or region."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the internet. Be specific and concise.",
                },
                "region": {
                    "type": "string",
                    "description": "Optional region code for localized results (e.g., 'us-en', 'uk-en', 'de-de'). Default: 'wt-wt' (worldwide).",
                    "default": "wt-wt",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10). Default: 3.",
                    "default": 3,
                },
            },
            "required": ["query"],
        }

    def execute(
        self, query: str, region: str = "wt-wt", max_results: int = 3, **kwargs
    ) -> str:
        """
        Execute a web search and return the top results (with caching).

        Args:
            query: Search query string
            region: Region code for localized results (default: 'wt-wt')
            max_results: Number of results to return (default: 3)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted string with search results and snippets
        """
        # Validate max_results
        max_results = max(1, min(10, max_results))

        # Check cache first
        cache = get_search_cache()
        cached_result = cache.get(
            self.name, query=query, region=region, max_results=max_results
        )

        if cached_result:
            return f"[Cached] {cached_result}"

        try:
            # Try to import duckduckgo_search
            from duckduckgo_search import DDGS

            # Perform search
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region=region, max_results=max_results))

            if not results:
                return f"No results found for query: {query}"

            # Format results
            formatted_results = f"Search results for '{query}'"
            if region != "wt-wt":
                formatted_results += f" (region: {region})"
            formatted_results += ":\n\n"

            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                snippet = result.get("body", "No description available")
                url = result.get("href", "")

                formatted_results += f"{i}. {title}\n"
                formatted_results += f"   {snippet}\n"
                if url:
                    formatted_results += f"   Source: {url}\n"
                formatted_results += "\n"

            final_result = formatted_results.strip()

            # Cache the result (TTL: 1 hour for general searches)
            cache.set(
                self.name,
                final_result,
                ttl=3600,
                query=query,
                region=region,
                max_results=max_results,
            )

            return final_result

        except ImportError:
            # Fallback if duckduckgo-search is not installed
            return (
                f"Web search unavailable: duckduckgo-search library not installed. "
                f"Query was: {query}\n\n"
                f"To enable web search, install: pip install duckduckgo-search"
            )
        except Exception as e:
            return f"Error performing web search: {str(e)}\nQuery was: {query}"

    def can_execute(self) -> bool:
        """
        Check if the web search tool can execute.

        Returns True even if duckduckgo_search is not installed,
        but the execute method will return an error message.
        """
        return True
