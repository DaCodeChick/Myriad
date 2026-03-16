"""
Roleplay feature tools - Limbic system function calling tools.

These tools manage the AI's internal emotional state through the limbic
system and digital pharmacy. Includes both natural emotional reactions
and substance-induced state changes.
"""

from core.features.roleplay.tools.inject_emotion import InjectEmotionTool
from core.features.roleplay.tools.consume_substance import ConsumeSubstanceTool

# Export all roleplay tools
ROLEPLAY_TOOLS = [
    InjectEmotionTool,
    ConsumeSubstanceTool,
]

__all__ = [
    "InjectEmotionTool",
    "ConsumeSubstanceTool",
    "ROLEPLAY_TOOLS",
]
