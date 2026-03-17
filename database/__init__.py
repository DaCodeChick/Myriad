"""
Database package for Project Myriad.

RDSSC Phase 3: Shared data access layer.

This package provides platform-agnostic database interfaces used across features:
- MemoryMatrix: Conversation memory facade (SQL + vector)
- GraphMemory: Knowledge graph operations
- VectorMemory: Semantic search via ChromaDB
- UserPreferences: Per-user settings

NOTE: This is infrastructure. Feature-specific database code lives in features/.
"""

from database.memory_matrix import MemoryMatrix
from database.vector_memory import VectorMemory
from database.graph_memory import GraphMemory
from database.user_preferences import UserPreferences

__all__ = [
    "MemoryMatrix",
    "VectorMemory",
    "GraphMemory",
    "UserPreferences",
]
