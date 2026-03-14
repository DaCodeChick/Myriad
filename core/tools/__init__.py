"""
Tool system for Project Myriad.

This module provides a modular tool system where each tool is a self-contained
module that can be easily added, removed, or modified without touching a central
monolithic registry.

Tools are implemented as classes inheriting from the Tool base class and are
automatically discovered and registered.
"""

from core.tools.base import Tool, ToolContext
from core.tools.get_current_time import GetCurrentTimeTool
from core.tools.roll_dice import RollDiceTool
from core.tools.add_knowledge import AddKnowledgeTool
from core.tools.inject_emotion import InjectEmotionTool
from core.tools.consume_substance import ConsumeSubstanceTool

__all__ = [
    "Tool",
    "ToolContext",
    "GetCurrentTimeTool",
    "RollDiceTool",
    "AddKnowledgeTool",
    "InjectEmotionTool",
    "ConsumeSubstanceTool",
]

# Registry of all available tool classes
BUILTIN_TOOLS = [
    GetCurrentTimeTool,
    RollDiceTool,
    AddKnowledgeTool,
    InjectEmotionTool,
    ConsumeSubstanceTool,
]
