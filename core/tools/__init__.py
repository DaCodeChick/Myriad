"""
Tool system for Project Myriad.

This module provides a modular, categorized tool system where each tool is a
self-contained module organized by category (utility, memory).

Tools are implemented as classes inheriting from the Tool base class and are
automatically discovered and registered.

Categories:
- utility: General-purpose helper tools (time, dice, etc.)
- memory: Knowledge graph and memory management tools

Note: Feature-specific tools (e.g., limbic tools for roleplay) are now registered
by their respective features.
"""

from core.tools.base import Tool, ToolContext

# Import tools from categorized subdirectories
from core.tools.utility import (
    GetCurrentTimeTool,
    RollDiceTool,
    SearchWebTool,
    SearchWebImagesTool,
    SearchNewsTool,
    ReadUrlTool,
    GenerateImageTool,
)
from core.tools.memory import AddKnowledgeTool

__all__ = [
    "Tool",
    "ToolContext",
    # Utility tools
    "GetCurrentTimeTool",
    "RollDiceTool",
    "SearchWebTool",
    "SearchWebImagesTool",
    "SearchNewsTool",
    "ReadUrlTool",
    "GenerateImageTool",
    # Memory tools
    "AddKnowledgeTool",
    # Registry
    "BUILTIN_TOOLS",
]

# Registry of all core (non-feature) tool classes
BUILTIN_TOOLS = [
    # Utility tools
    GetCurrentTimeTool,
    RollDiceTool,
    SearchWebTool,
    SearchWebImagesTool,
    SearchNewsTool,
    ReadUrlTool,
    GenerateImageTool,
    # Memory tools
    AddKnowledgeTool,
]
