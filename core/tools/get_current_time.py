"""
Get Current Time tool - Returns current date and time.

Part of RDSSC Phase 7: Modularized tool system.
"""

from datetime import datetime
from typing import Dict, Any
from core.tools.base import Tool


class GetCurrentTimeTool(Tool):
    """Tool for getting the current date and time."""

    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "Get the current date and time. Use this when the user asks about the current time, date, day of the week, or any time-related query."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self) -> str:
        """Return the current date and time as a formatted string."""
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y at %I:%M %p")
