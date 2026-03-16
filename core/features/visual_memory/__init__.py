"""
Visual Memory Feature - Character visual profiles and image generation.

Exports:
- VisualMemoryFeature: Main feature class
- VisualManager: Core engine (platform-agnostic)
"""

from core.features.visual_memory.visual_memory_feature import VisualMemoryFeature
from core.features.visual_memory.visual_manager import VisualManager

__all__ = [
    "VisualMemoryFeature",
    "VisualManager",
]
