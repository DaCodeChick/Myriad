"""
Tool system for Project Myriad.

This module provides a modular, categorized tool system where each tool is a
self-contained module organized by category (utility, memory, limbic).

Tools are implemented as classes inheriting from the Tool base class and are
automatically discovered and registered.

Categories:
- utility: General-purpose helper tools (time, dice, etc.)
- memory: Knowledge graph and memory management tools
- limbic: Neurochemical state and emotional regulation tools (including pharmacy)
"""

from core.tools.base import Tool, ToolContext

# Import tools from categorized subdirectories
from core.tools.utility import GetCurrentTimeTool, RollDiceTool, SearchWebTool
from core.tools.memory import AddKnowledgeTool
from core.tools.limbic import InjectEmotionTool, ConsumeSubstanceTool

__all__ = [
    "Tool",
    "ToolContext",
    # Utility tools
    "GetCurrentTimeTool",
    "RollDiceTool",
    "SearchWebTool",
    # Memory tools
    "AddKnowledgeTool",
    # Limbic tools
    "InjectEmotionTool",
    "ConsumeSubstanceTool",
    # Registry
    "BUILTIN_TOOLS",
]

# Registry of all available tool classes
BUILTIN_TOOLS = [
    # Utility tools
    GetCurrentTimeTool,
    RollDiceTool,
    SearchWebTool,
    # Memory tools
    AddKnowledgeTool,
    # Limbic tools
    InjectEmotionTool,
    ConsumeSubstanceTool,
]
