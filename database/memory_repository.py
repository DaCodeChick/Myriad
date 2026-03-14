"""
Core memory repository for Project Myriad.

This module handles CRUD operations for conversational memories including:
- Adding memories to SQL and vector stores
- Retrieving conversation context
- Semantic search across memories
- Clearing user memories

Part of RDSSC Phase 5: Split memory_matrix.py into focused modules.
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class MemoryRepository:
    """Handles core CRUD operations for conversational memories."""

    def __init__(self, db_path: str, vector_memory=None):
        """
        Initialize memory repository.

        Args:
            db_path: Path to SQLite database file
            vector_memory: Optional VectorMemory instance for semantic search
        """
        self.db_path = db_path
        self.vector_memory = vector_memory
        self.vector_memory_enabled = vector_memory is not None
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Ensure memories table exists."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                origin_persona TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                visibility_scope TEXT NOT NULL,
                life_id TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )

        # Create indices for common queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_life ON memories(life_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_persona ON memories(origin_persona)"
        )

        conn.commit()
        conn.close()

    def add_memory(
        self,
        user_id: str,
        origin_persona: str,
        role: str,
        content: str,
        visibility_scope: str,
        life_id: str,
        importance_score: int = 5,
    ) -> int:
        """
        Add a memory to both SQL and vector storage.

        Args:
            user_id: User identifier
            origin_persona: Persona that created this memory
            role: Message role (user/assistant/system)
            content: Message content
            visibility_scope: GLOBAL, USER_SHARED, or ISOLATED
            life_id: Timeline identifier
            importance_score: Importance rating 1-10 (default: 5)

        Returns:
            Memory ID (primary key)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO memories (user_id, origin_persona, role, content, visibility_scope, life_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                origin_persona,
                role,
                content,
                visibility_scope,
                life_id,
                timestamp,
            ),
        )

        memory_id = cursor.lastrowid or 0
        conn.commit()
        conn.close()

        # Also add to vector memory if enabled (with importance_score)
        if self.vector_memory_enabled and self.vector_memory:
            try:
                self.vector_memory.add_memory(
                    memory_id=str(memory_id),
                    user_id=user_id,
                    origin_persona=origin_persona,
                    role=role,
                    content=content,
                    visibility_scope=visibility_scope,
                    life_id=life_id,
                    timestamp=timestamp,
                    importance_score=importance_score,
                )
            except Exception as e:
                print(f"Warning: Failed to add to vector memory: {e}")

        return memory_id

    def get_context(
        self,
        user_id: Optional[str],
        persona_id: Optional[str],
        life_id: Optional[str],
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation context for a user.

        Retrieves memories that are either:
        - Created by the current persona (ISOLATED scope)
        - Marked as GLOBAL (visible across all users and personas)
        - Marked as USER_SHARED (visible across all personas for this user)

        OOC Mode: If user_id/persona_id are None, returns ALL memories (no filtering).

        Args:
            user_id: User identifier (None for OOC global access)
            persona_id: Current active persona (None for OOC global access)
            life_id: Current timeline (None for OOC global access)
            limit: Maximum number of messages to retrieve

        Returns:
            List of memory dictionaries with keys: id, role, content, timestamp
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # OOC Mode: Global access to ALL memories
        if user_id is None:
            cursor.execute(
                """
                SELECT id, role, content, timestamp, user_id, origin_persona, life_id
                FROM memories
                ORDER BY id DESC
                LIMIT ?
            """,
                (limit,),
            )
        else:
            # Normal mode: Automated Discretion Engine filtering
            cursor.execute(
                """
                SELECT id, role, content, timestamp
                FROM memories
                WHERE user_id = ?
                  AND life_id = ?
                  AND (origin_persona = ? OR visibility_scope = 'GLOBAL' OR visibility_scope = 'USER_SHARED')
                ORDER BY id DESC
                LIMIT ?
            """,
                (user_id, life_id or "", persona_id, limit),
            )

        rows = cursor.fetchall()
        conn.close()

        # Return in chronological order (oldest first)
        return [dict(row) for row in reversed(rows)]

    def get_all_memories(
        self, user_id: str, persona_id: str, life_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a user in the current timeline.

        Args:
            user_id: User identifier
            persona_id: Current active persona
            life_id: Current timeline

        Returns:
            List of all memory dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, role, content, timestamp, origin_persona, visibility_scope
            FROM memories
            WHERE user_id = ?
              AND life_id = ?
              AND (origin_persona = ? OR visibility_scope = 'GLOBAL')
            ORDER BY id ASC
        """,
            (user_id, life_id, persona_id),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_semantic(
        self,
        user_id: str,
        persona_id: str,
        life_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across memories using vector similarity.

        Args:
            user_id: User identifier
            persona_id: Current active persona
            life_id: Current timeline
            query: Search query text
            top_k: Number of results to return

        Returns:
            List of relevant memory dictionaries with similarity scores
        """
        if not self.vector_memory_enabled or not self.vector_memory:
            return []

        try:
            return self.vector_memory.search_semantic_memories(
                query=query,
                user_id=user_id,
                current_persona=persona_id,
                top_k=top_k,
                life_id=life_id,
            )
        except Exception as e:
            print(f"Warning: Vector search failed: {e}")
            return []

    def clear_memories(self, user_id: str, persona_id: Optional[str] = None) -> None:
        """
        Clear all memories for a user.

        Args:
            user_id: User identifier
            persona_id: If provided, only clear memories for this persona (ISOLATED scope)
                       If None, clear all memories for the user
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if persona_id:
            # Only clear ISOLATED memories for this persona
            cursor.execute(
                "DELETE FROM memories WHERE user_id = ? AND origin_persona = ? AND visibility_scope = 'ISOLATED'",
                (user_id, persona_id),
            )
        else:
            cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))

        conn.commit()
        conn.close()

        # Also clear from vector memory if enabled
        if self.vector_memory_enabled and self.vector_memory:
            try:
                self.vector_memory.clear_user_memories(user_id, persona_id)
            except Exception as e:
                print(f"Warning: Failed to clear vector memories: {e}")
