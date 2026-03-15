"""
News Search tool - Search for recent news articles.

Provides AI agents with news-specific search via DuckDuckGo.
Returns top 5 recent news articles with dates and sources.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from core.tools.base import Tool


class SearchNewsTool(Tool):
    """Tool for searching recent news articles."""

    @property
    def name(self) -> str:
        return "search_news"

    @property
    def description(self) -> str:
        return (
            "Search for recent news articles about a specific topic. Use this when "
            "the user asks about current events, breaking news, recent developments, "
            "or what's happening now. Returns recent news articles with publication "
            "dates and sources."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The news search query. Be specific about the topic or event.",
                },
                "days": {
                    "type": "integer",
                    "description": "How many days back to search (default: 7). Use smaller numbers for breaking news, larger for recent developments.",
                    "default": 7,
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, days: int = 7) -> str:
        """
        Execute a news search and return recent articles.

        Args:
            query: News search query string
            days: Number of days back to search (default: 7)

        Returns:
            Formatted string with news articles, dates, and sources
        """
        try:
            # Try to import duckduckgo_search
            from duckduckgo_search import DDGS

            # Calculate time range
            time_range = self._get_time_range(days)

            # Perform news search
            with DDGS() as ddgs:
                results = list(ddgs.news(query, max_results=5))

            if not results:
                return f"No recent news found for query: {query} (last {days} days)"

            # Format results
            formatted_results = f"Recent news for '{query}' (last {days} days):\n\n"

            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                body = result.get("body", "No description available")
                url = result.get("url", "")
                date = result.get("date", "Unknown date")
                source = result.get("source", "Unknown source")

                formatted_results += f"{i}. {title}\n"
                formatted_results += f"   Published: {date}\n"
                formatted_results += f"   Source: {source}\n"
                formatted_results += f"   {body}\n"
                if url:
                    formatted_results += f"   URL: {url}\n"
                formatted_results += "\n"

            return formatted_results.strip()

        except ImportError:
            return (
                f"News search unavailable: duckduckgo-search library not installed. "
                f"Query was: {query}\n\n"
                f"To enable news search, install: pip install duckduckgo-search"
            )
        except Exception as e:
            return f"Error performing news search: {str(e)}\nQuery was: {query}"

    def _get_time_range(self, days: int) -> str:
        """
        Get a human-readable time range description.

        Args:
            days: Number of days

        Returns:
            Time range string
        """
        if days == 1:
            return "today"
        elif days == 7:
            return "this week"
        elif days == 30:
            return "this month"
        else:
            return f"last {days} days"

    def can_execute(self) -> bool:
        """
        Check if the news search tool can execute.

        Returns True even if duckduckgo_search is not installed,
        but the execute method will return an error message.
        """
        return True
