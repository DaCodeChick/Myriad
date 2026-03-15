"""
Read URL tool - Fetch and extract clean text from a webpage.

Provides AI agents with the ability to read the actual content of webpages.
Returns clean, readable text with HTML/CSS/JavaScript stripped.
"""

from typing import Dict, Any
from core.tools.base import Tool


class ReadUrlTool(Tool):
    """Tool for fetching and reading webpage content."""

    @property
    def name(self) -> str:
        return "read_url"

    @property
    def description(self) -> str:
        return (
            "Read the full text content of a specific webpage by URL. Use this tool "
            "when you need to access the actual content of a website, article, or "
            "documentation page. The tool fetches the page, strips HTML/CSS/JavaScript, "
            "and returns clean, readable text. Perfect for reading articles, documentation, "
            "blog posts, or any web content the user provides or you discover through search."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the webpage to read (must start with http:// or https://).",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum number of characters to return (default: 10000). Use lower values for summaries.",
                    "default": 10000,
                },
            },
            "required": ["url"],
        }

    def execute(self, url: str, max_chars: int = 10000, **kwargs) -> str:
        """
        Fetch and extract clean text from a webpage.

        Args:
            url: The URL to fetch
            max_chars: Maximum characters to return (default: 10000)
            **kwargs: Additional arguments (ignored)

        Returns:
            Clean text content of the webpage
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                return f"Invalid URL: {url}\nURL must start with http:// or https://"

            # Validate max_chars
            max_chars = max(100, min(50000, max_chars))  # Clamp between 100-50000

            # Try to import required libraries
            try:
                import requests
                from bs4 import BeautifulSoup
            except ImportError as e:
                missing_lib = str(e).split("'")[1] if "'" in str(e) else "unknown"
                return (
                    f"URL reading unavailable: {missing_lib} library not installed.\n"
                    f"To enable URL reading, install: pip install requests beautifulsoup4"
                )

            # Fetch the webpage
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes

            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script, style, and other non-content elements
            for element in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "header",
                    "aside",
                    "iframe",
                    "noscript",
                ]
            ):
                element.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive whitespace
            lines = [line.strip() for line in text.splitlines()]
            lines = [line for line in lines if line]  # Remove empty lines
            clean_text = "\n".join(lines)

            # Get metadata
            title = soup.find("title")
            title_text = title.get_text(strip=True) if title else "No title"

            # Truncate if needed
            if len(clean_text) > max_chars:
                clean_text = clean_text[:max_chars]
                truncated = True
            else:
                truncated = False

            # Format result
            result = f"Page Title: {title_text}\n"
            result += f"URL: {url}\n"
            result += f"Content Length: {len(clean_text)} characters"
            if truncated:
                result += f" (truncated from original)\n"
            else:
                result += "\n"
            result += "\n" + "=" * 50 + "\n\n"
            result += clean_text

            if truncated:
                result += f"\n\n[Content truncated at {max_chars} characters. Original page is longer.]"

            return result

        except requests.exceptions.Timeout:
            return f"Error: Request timed out while fetching {url}\nThe server took too long to respond (>10 seconds)."

        except requests.exceptions.ConnectionError:
            return f"Error: Connection failed for {url}\nCould not connect to the server. Check if the URL is correct."

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 404:
                return f"Error: Page not found (404)\nURL: {url}\nThe requested page does not exist."
            elif status_code == 403:
                return f"Error: Access forbidden (403)\nURL: {url}\nThe server is blocking automated access to this page."
            elif status_code == 500:
                return f"Error: Server error (500)\nURL: {url}\nThe website is experiencing technical difficulties."
            else:
                return f"Error: HTTP {status_code}\nURL: {url}\n{str(e)}"

        except Exception as e:
            return f"Error reading URL: {str(e)}\nURL: {url}"

    def can_execute(self) -> bool:
        """
        Check if the URL reading tool can execute.

        Returns True even if libraries aren't installed,
        but the execute method will return an error message.
        """
        return True
