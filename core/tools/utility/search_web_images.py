"""
Web Image Search tool - Search for images on the internet.

Provides AI agents with image search capabilities via DuckDuckGo.
Returns top 5 image results with URLs and descriptions. Includes rate limiting.
"""

from typing import Dict, Any
from core.tools.base import Tool
from core.tools.utility.search_cache import get_rate_limiter


class SearchWebImagesTool(Tool):
    """Tool for searching the internet for images."""

    @property
    def name(self) -> str:
        return "search_web_images"

    @property
    def description(self) -> str:
        return (
            "Search the internet for images. Use this when the user asks to find, "
            "show, or look up images, photos, pictures, or visual content. Returns "
            "image URLs and descriptions that can be shared with the user."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The image search query. Be specific and descriptive.",
                }
            },
            "required": ["query"],
        }

    def execute(self, **kwargs) -> str:
        """
        Execute an image search and return the top 5 results (with rate limiting).

        Args:
            query: Image search query string

        Returns:
            Formatted string with image URLs and descriptions
        """
        query = kwargs.get("query", "")

        if not query:
            return "Error: No search query provided"

        # Check rate limit
        rate_limiter = get_rate_limiter()
        if not rate_limiter.allow_request():
            wait_time = rate_limiter.get_wait_time()
            return (
                f"Rate limit exceeded. Please wait {wait_time:.1f} seconds before "
                f"making another search request. (Limit: 30 requests per minute)"
            )

        try:
            # Try to import duckduckgo_search
            from duckduckgo_search import DDGS

            # Perform image search
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=5))

            if not results:
                return f"No images found for query: {query}"

            # Format results
            formatted_results = f"Image search results for '{query}':\n\n"

            for i, result in enumerate(results, 1):
                title = result.get("title", "Untitled")
                url = result.get("image", "")
                thumbnail = result.get("thumbnail", "")
                source = result.get("source", "Unknown source")
                width = result.get("width", "?")
                height = result.get("height", "?")

                formatted_results += f"{i}. {title}\n"
                formatted_results += f"   Resolution: {width}x{height}\n"
                formatted_results += f"   Image URL: {url}\n"
                formatted_results += f"   Thumbnail: {thumbnail}\n"
                formatted_results += f"   Source: {source}\n"
                formatted_results += "\n"

            formatted_results += "Note: You can share these image URLs with the user.\n"

            return formatted_results.strip()

        except ImportError:
            return (
                f"Image search unavailable: duckduckgo-search library not installed. "
                f"Query was: {query}\n\n"
                f"To enable image search, install: pip install duckduckgo-search"
            )
        except Exception as e:
            return f"Error performing image search: {str(e)}\nQuery was: {query}"

    def can_execute(self) -> bool:
        """
        Check if the image search tool can execute.

        Returns True even if duckduckgo_search is not installed,
        but the execute method will return an error message.
        """
        return True
