"""
SQLite Memory Matrix - The central database for Project Myriad.

This module handles:
1. User state tracking (active_persona_id per user)
2. Conversation memory with visibility scoping (GLOBAL vs ISOLATED)
3. The Automated Discretion Engine routing logic
4. Semantic vector memory integration via ChromaDB
"""

import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.vector_memory import VectorMemory


class MemoryMatrix:
    """Manages all database operations for Project Myriad."""

    def __init__(
        self,
        db_path: str = "database/myriad_state.db",
        vector_memory_enabled: bool = True,
    ):
        """Initialize the database connection and ensure schema exists."""
        self.db_path = db_path
        self.vector_memory_enabled = vector_memory_enabled

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize SQLite schema
        self._init_schema()

        # Initialize VectorMemory if enabled
        if self.vector_memory_enabled:
            try:
                self.vector_memory = VectorMemory()
            except Exception as e:
                print(f"Warning: Failed to initialize VectorMemory: {e}")
                print("Continuing with SQLite-only memory system.")
                self.vector_memory_enabled = False
                self.vector_memory = None
        else:
            self.vector_memory = None

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allow dict-like access to rows
        return conn

    def _init_schema(self):
        """Create all necessary tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # User State Table - tracks active persona per user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_state (
                user_id TEXT PRIMARY KEY,
                active_persona_id TEXT NOT NULL,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Memory Table - conversation history with visibility scoping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                origin_persona TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                visibility_scope TEXT NOT NULL CHECK(visibility_scope IN ('GLOBAL', 'ISOLATED')),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_id) REFERENCES user_state(user_id)
            )
        """)

        # Create indexes for fast querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_user 
            ON memories(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_visibility 
            ON memories(visibility_scope)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_timestamp 
            ON memories(timestamp DESC)
        """)

        conn.commit()
        conn.close()

    # ========================
    # USER STATE MANAGEMENT
    # ========================

    def get_active_persona(self, user_id: str) -> Optional[str]:
        """
        Get the currently active persona for a user.

        Args:
            user_id: Discord user ID (as string)

        Returns:
            persona_id if user exists, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT active_persona_id FROM user_state WHERE user_id = ?", (user_id,)
        )

        result = cursor.fetchone()
        conn.close()

        return result["active_persona_id"] if result else None

    def set_active_persona(self, user_id: str, persona_id: str):
        """
        Set or update the active persona for a user.

        Args:
            user_id: Discord user ID (as string)
            persona_id: The persona to activate
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_persona_id, last_interaction)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                active_persona_id = excluded.active_persona_id,
                last_interaction = CURRENT_TIMESTAMP
        """,
            (user_id, persona_id),
        )

        conn.commit()
        conn.close()

    def update_user_interaction(self, user_id: str):
        """Update the last interaction timestamp for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_state 
            SET last_interaction = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        """,
            (user_id,),
        )

        conn.commit()
        conn.close()

    # ========================
    # MEMORY MANAGEMENT
    # ========================

    def add_memory(
        self,
        user_id: str,
        origin_persona: str,
        role: str,
        content: str,
        visibility_scope: str = "ISOLATED",
    ) -> int:
        """
        Add a new memory to the database.

        Args:
            user_id: Discord user ID
            origin_persona: The persona_id that recorded this memory
            role: 'user', 'assistant', or 'system'
            content: The message content
            visibility_scope: 'GLOBAL' or 'ISOLATED' (default: ISOLATED)

        Returns:
            The ID of the inserted memory
        """
        if visibility_scope not in ("GLOBAL", "ISOLATED"):
            raise ValueError("visibility_scope must be 'GLOBAL' or 'ISOLATED'")

        if role not in ("user", "assistant", "system"):
            raise ValueError("role must be 'user', 'assistant', or 'system'")

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO memories (user_id, origin_persona, role, content, visibility_scope)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user_id, origin_persona, role, content, visibility_scope),
        )

        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Also add to vector memory if enabled
        if self.vector_memory_enabled and self.vector_memory:
            try:
                self.vector_memory.add_memory(
                    memory_id=str(memory_id),
                    user_id=user_id,
                    origin_persona=origin_persona,
                    role=role,
                    content=content,
                    visibility_scope=visibility_scope,
                )
            except Exception as e:
                print(f"Warning: Failed to add memory to vector store: {e}")

        # lastrowid should always exist for INSERT, but satisfy type checker
        assert memory_id is not None
        return memory_id

    def get_context_memories(
        self, user_id: str, current_persona: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories for context injection using the Automated Discretion Engine.

        Returns memories where:
        - visibility_scope = 'GLOBAL' (shared across all personas), OR
        - origin_persona = current_persona (isolated to this persona)

        Args:
            user_id: Discord user ID
            current_persona: The currently active persona_id
            limit: Maximum number of memories to return (chronological, most recent)

        Returns:
            List of memory dictionaries, ordered by timestamp (oldest first for LLM context)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, origin_persona, role, content, visibility_scope, timestamp
            FROM memories
            WHERE user_id = ?
              AND (visibility_scope = 'GLOBAL' OR origin_persona = ?)
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (user_id, current_persona, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        # Convert to list of dicts and reverse (oldest first for context)
        memories = [dict(row) for row in rows]
        memories.reverse()

        return memories

    def get_all_memories_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get ALL memories for a specific user (admin/debug function).

        Args:
            user_id: Discord user ID

        Returns:
            List of all memory dictionaries for this user
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, origin_persona, role, content, visibility_scope, timestamp
            FROM memories
            WHERE user_id = ?
            ORDER BY timestamp ASC
        """,
            (user_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_semantic_memories(
        self,
        user_id: str,
        current_persona: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar memories using vector embeddings.

        This uses the Automated Discretion Engine to filter results by:
        - visibility_scope = 'GLOBAL' (shared across all personas), OR
        - origin_persona = current_persona (isolated to this persona)

        Args:
            user_id: Discord user ID
            current_persona: The currently active persona_id
            query: The text to search for semantically similar memories
            limit: Maximum number of memories to return (default: 5)

        Returns:
            List of memory dictionaries with semantic similarity scores,
            ordered by relevance (most similar first)
        """
        if not self.vector_memory_enabled or not self.vector_memory:
            # Fallback: return empty list if vector memory is disabled
            return []

        try:
            return self.vector_memory.search_semantic_memories(
                query=query,
                user_id=user_id,
                current_persona=current_persona,
                top_k=limit,
            )
        except Exception as e:
            print(f"Warning: Semantic search failed: {e}")
            return []

    def clear_user_memories(self, user_id: str, persona_id: Optional[str] = None):
        """
        Clear memories for a user.

        Args:
            user_id: Discord user ID
            persona_id: If provided, only clear memories from this persona.
                       If None, clear ALL memories for the user.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if persona_id:
            cursor.execute(
                "DELETE FROM memories WHERE user_id = ? AND origin_persona = ?",
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
