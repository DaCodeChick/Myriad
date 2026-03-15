"""
Web Search tool - Search the internet for real-time information.

Provides AI agents with real-time internet access via DuckDuckGo search.
Returns top 3 search results with snippets.
"""

from typing import Dict, Any
from core.tools.base import Tool


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
            "the user asks about recent events, current news, or real-time information."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the internet. Be specific and concise.",
                }
            },
            "required": ["query"],
        }

    def execute(self, query: str) -> str:
        """
        Execute a web search and return the top 3 results.

        Args:
            query: Search query string

        Returns:
            Formatted string with search results and snippets
        """
        try:
            # Try to import duckduckgo_search
            from duckduckgo_search import DDGS

            # Perform search
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))

            if not results:
                return f"No results found for query: {query}"

            # Format results
            formatted_results = f"Search results for '{query}':\n\n"

            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                snippet = result.get("body", "No description available")
                url = result.get("href", "")

                formatted_results += f"{i}. {title}\n"
                formatted_results += f"   {snippet}\n"
                if url:
                    formatted_results += f"   Source: {url}\n"
                formatted_results += "\n"

            return formatted_results.strip()

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
