"""
Limbic tools - Neurochemical state and emotional regulation tools.

These tools manage the AI's internal emotional state through the limbic
system and digital pharmacy. Includes both natural emotional reactions
and substance-induced state changes.
"""

from core.tools.limbic.inject_emotion import InjectEmotionTool
from core.tools.limbic.consume_substance import ConsumeSubstanceTool

__all__ = [
    "InjectEmotionTool",
    "ConsumeSubstanceTool",
]
