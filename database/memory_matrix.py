"""
SQLite Memory Matrix - Facade for Project Myriad's memory subsystems.

This module provides a unified interface to:
1. User state management (active persona tracking)
2. Memory repository (conversation storage and retrieval)
3. Lives memory operations (timeline branching and management)
4. Semantic vector memory integration via ChromaDB

ENSEMBLE MODE: Supports multiple active personas simultaneously.

Part of RDSSC Phase 5: Refactored to delegate to focused modules.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.lives_memory import LivesMemoryManager
from database.memory_repository import MemoryRepository
from database.user_state import UserStateManager
from database.vector_memory import VectorMemory


class MemoryMatrix:
    """
    Facade for memory operations.

    Delegates to specialized modules:
    - UserStateManager: Active persona and interaction tracking
    - MemoryRepository: Core memory CRUD operations
    - LivesMemoryManager: Timeline-specific memory operations
    """

    def __init__(
        self,
        db_path: str = "data/myriad_state.db",
        vector_memory_enabled: bool = True,
    ):
        """Initialize the memory subsystems."""
        self.db_path = db_path
        self.vector_memory_enabled = vector_memory_enabled

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize vector memory first (if enabled)
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

        # Initialize SQLite schema (ensures tables exist)
        self._init_schema()

        # Initialize subsystem managers
        self.user_state = UserStateManager(db_path)
        self.memory_repo = MemoryRepository(db_path, self.vector_memory)
        self.lives_memory = LivesMemoryManager(db_path, self.vector_memory)

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allow dict-like access to rows
        return conn

    def _init_schema(self) -> None:
        """Create all necessary tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # User State Table - tracks active persona per user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_state (
                user_id TEXT PRIMARY KEY,
                active_persona TEXT,
                last_interaction_time TEXT
            )
        """)

        # Memory Table - conversation history with visibility scoping and life scoping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                origin_persona TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                visibility_scope TEXT NOT NULL CHECK(visibility_scope IN ('GLOBAL', 'ISOLATED')),
                life_id TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # MIGRATION: Add life_id column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(memories)")
        columns = [col[1] for col in cursor.fetchall()]
        if "life_id" not in columns:
            print("⚠ Migrating memories table: Adding life_id column...")
            cursor.execute("ALTER TABLE memories ADD COLUMN life_id TEXT")
            print("✓ Migration complete")

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

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_life
            ON memories(life_id)
        """)

        conn.commit()
        conn.close()

    # ========================
    # USER STATE MANAGEMENT
    # (Delegated to UserStateManager - Extended for Ensemble Mode)
    # ========================

    def get_active_personas(self, user_id: str) -> List[str]:
        """
        Get all currently active personas for a user (Ensemble Mode).

        Args:
            user_id: Discord user ID (as string)

        Returns:
            List of persona_ids (empty list if none active)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT active_persona_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return []

        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return []

    def add_active_persona(self, user_id: str, persona_id: str) -> None:
        """
        Add a persona to the active ensemble (appends to list).

        Args:
            user_id: Discord user ID (as string)
            persona_id: The persona to add
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current personas
        cursor.execute(
            "SELECT active_persona_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()

        current_personas = []
        if row and row[0]:
            try:
                current_personas = json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                current_personas = []

        # Add new persona if not already in list
        if persona_id not in current_personas:
            current_personas.append(persona_id)

        # Update database
        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_persona_ids)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_persona_ids = excluded.active_persona_ids
        """,
            (user_id, json.dumps(current_personas)),
        )

        conn.commit()
        conn.close()

    def remove_active_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Remove a specific persona from the active ensemble.

        Args:
            user_id: Discord user ID (as string)
            persona_id: The persona to remove

        Returns:
            True if persona was removed, False if it wasn't in the list
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current personas
        cursor.execute(
            "SELECT active_persona_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()

        if not row or not row[0]:
            conn.close()
            return False

        try:
            current_personas = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            conn.close()
            return False

        # Remove persona if present
        if persona_id in current_personas:
            current_personas.remove(persona_id)

            # Update database
            cursor.execute(
                """
                UPDATE user_state 
                SET active_persona_ids = ? 
                WHERE user_id = ?
            """,
                (json.dumps(current_personas), user_id),
            )

            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    def clear_active_personas(self, user_id: str) -> None:
        """
        Clear all active personas for a user.

        Args:
            user_id: Discord user ID (as string)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_state 
            SET active_persona_ids = NULL 
            WHERE user_id = ?
        """,
            (user_id,),
        )

        conn.commit()
        conn.close()

    def get_active_persona(self, user_id: str) -> Optional[str]:
        """
        Get the first active persona for a user (legacy method for backwards compatibility).

        Args:
            user_id: Discord user ID (as string)

        Returns:
            persona_id if user exists, None otherwise
        """
        personas = self.get_active_personas(user_id)
        return personas[0] if personas else None

    def set_active_persona(self, user_id: str, persona_id: str) -> None:
        """
        Set a single active persona (legacy method - clears other personas).

        Args:
            user_id: Discord user ID (as string)
            persona_id: The persona to activate
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_persona_ids)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_persona_ids = excluded.active_persona_ids
        """,
            (user_id, json.dumps([persona_id])),
        )

        conn.commit()
        conn.close()

    def update_user_interaction(self, user_id: str) -> None:
        """Update the last interaction timestamp for a user."""
        self.user_state.update_last_interaction(user_id)

    # ========================
    # MEMORY MANAGEMENT
    # (Delegated to MemoryRepository)
    # ========================

    def add_memory(
        self,
        user_id: str,
        origin_persona: str,
        role: str,
        content: str,
        visibility_scope: str = "ISOLATED",
        life_id: Optional[str] = None,
    ) -> int:
        """
        Add a new memory to the database.

        Args:
            user_id: Discord user ID
            origin_persona: The persona_id that recorded this memory
            role: 'user', 'assistant', or 'system'
            content: The message content
            visibility_scope: 'GLOBAL' or 'ISOLATED' (default: ISOLATED)
            life_id: Timeline/session ID (optional for backwards compatibility)

        Returns:
            The ID of the inserted memory
        """
        if visibility_scope not in ("GLOBAL", "ISOLATED"):
            raise ValueError("visibility_scope must be 'GLOBAL' or 'ISOLATED'")

        if role not in ("user", "assistant", "system"):
            raise ValueError("role must be 'user', 'assistant', or 'system'")

        # Default life_id to empty string if None (for backwards compatibility)
        if life_id is None:
            life_id = ""

        return self.memory_repo.add_memory(
            user_id=user_id,
            origin_persona=origin_persona,
            role=role,
            content=content,
            visibility_scope=visibility_scope,
            life_id=life_id,
        )

    def get_context_memories(
        self,
        user_id: Optional[str],
        current_persona: Optional[str],
        limit: int = 50,
        life_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories for context injection using the Automated Discretion Engine.

        Returns memories where:
        - visibility_scope = 'GLOBAL' (shared across all personas), OR
        - origin_persona = current_persona (isolated to this persona)
        - life_id = current life (if provided)

        OOC Mode: If user_id/current_persona are None, returns ALL memories (no filtering).

        Args:
            user_id: Discord user ID (None for OOC global access)
            current_persona: The currently active persona_id (None for OOC global access)
            limit: Maximum number of memories to return (chronological, most recent)
            life_id: Optional life/timeline ID to filter by (None for OOC global access)

        Returns:
            List of memory dictionaries, ordered by timestamp (oldest first for LLM context)
        """
        # Default life_id to empty string if None (except in OOC mode)
        if life_id is None and user_id is not None:
            life_id = ""

        return self.memory_repo.get_context(
            user_id=user_id,
            persona_id=current_persona,
            life_id=life_id,
            limit=limit,
        )

    def search_semantic_memories(
        self,
        user_id: Optional[str],
        current_persona: Optional[str],
        query: str,
        limit: int = 5,
        life_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search semantic vector memories using the Automated Discretion Engine.

        OOC Mode: If user_id/current_persona are None, searches ALL memories (no filtering).

        Args:
            user_id: User identifier (None for OOC global access)
            current_persona: Active persona (None for OOC global access)
            query: Search query
            limit: Number of results
            life_id: Optional life ID (None for OOC global access)

        Returns:
            List of semantically relevant memories
        """
        # Default life_id to empty string if None (except in OOC mode)
        if life_id is None and user_id is not None:
            life_id = ""

        return self.memory_repo.search_semantic(
            user_id=user_id or "",  # VectorMemory needs a string, not None
            persona_id=current_persona or "",
            life_id=life_id or "",
            query=query,
            top_k=limit,
        )

    def get_all_memories_for_user(
        self, user_id: str, persona_id: str = "", life_id: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get ALL memories for a specific user (admin/debug function).

        Args:
            user_id: Discord user ID
            persona_id: Optional persona filter (default: empty = all personas)
            life_id: Optional life filter (default: empty = current life)

        Returns:
            List of all memory dictionaries for this user
        """
        return self.memory_repo.get_all_memories(
            user_id=user_id, persona_id=persona_id, life_id=life_id
        )

    def clear_user_memories(
        self, user_id: str, persona_id: Optional[str] = None
    ) -> None:
        """
        Clear memories for a user.

        Args:
            user_id: Discord user ID
            persona_id: If provided, only clear memories from this persona.
                       If None, clear ALL memories for the user.
        """
        self.memory_repo.clear_memories(user_id=user_id, persona_id=persona_id)

    # ========================
    # LIVES & MEMORIES SYSTEM
    # (Delegated to LivesMemoryManager)
    # ========================

    def delete_memories_after_checkpoint(
        self, life_id: str, checkpoint_message_id: int
    ) -> int:
        """
        Delete all memories (SQL + vector) that occurred AFTER a checkpoint.
        Used when loading a save state with FORGET option.

        Args:
            life_id: The timeline ID
            checkpoint_message_id: Delete all memories with id > this value

        Returns:
            Number of memories deleted
        """
        return self.lives_memory.delete_memories_after_checkpoint(
            life_id=life_id, checkpoint_message_id=checkpoint_message_id
        )

    def clone_life_memories(
        self,
        source_life_id: str,
        target_life_id: str,
        up_to_message_id: Optional[int] = None,
    ) -> int:
        """
        Clone all memories from one life to another.
        Used when creating a branch before rewinding.

        Args:
            source_life_id: The life to copy from
            target_life_id: The life to copy to
            up_to_message_id: Optional - only clone up to this message ID

        Returns:
            Number of memories cloned
        """
        return self.lives_memory.clone_life_memories(
            source_life_id=source_life_id,
            target_life_id=target_life_id,
            up_to_message_id=up_to_message_id,
        )
