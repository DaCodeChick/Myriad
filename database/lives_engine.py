"""
Lives Engine - Session/Timeline Management for Project Myriad.

This module implements the "Lives" system - allowing users to create multiple
parallel timelines with the same persona. Think of it like a Visual Novel or RPG
with alternate routes and branches.

Architecture:
- Each user+persona pair can have multiple "lives" (parallel timelines)
- One life is "active" at a time
- Messages and memories are scoped to specific life_id
- Lives can be created, switched, listed, and deleted
- Each life has a name and description for easy identification

Database Schema:
    lives (
        life_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        persona_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP,
        is_active INTEGER DEFAULT 0,
        UNIQUE(user_id, persona_id, name)
    )
"""

import sqlite3
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime


class LivesEngine:
    """Manages timeline/session state for users and personas."""

    def __init__(self, db_path: str = "data/myriad_state.db"):
        """
        Initialize the Lives Engine.

        Args:
            db_path: Path to SQLite database (shared with MemoryMatrix)
        """
        self.db_path = db_path

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize schema
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        """Create lives table if it doesn't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lives (
                life_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 0,
                
                UNIQUE(user_id, persona_id, name)
            )
        """)

        # Create indexes for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lives_user_persona
            ON lives(user_id, persona_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lives_active
            ON lives(user_id, persona_id, is_active)
        """)

        conn.commit()
        conn.close()

    # ========================
    # LIFE MANAGEMENT
    # ========================

    def create_life(
        self,
        user_id: str,
        persona_id: str,
        name: str,
        description: Optional[str] = None,
        set_active: bool = False,
    ) -> str:
        """
        Create a new life (timeline) for a user+persona pair.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            name: Name for this life/timeline
            description: Optional description
            set_active: Whether to set this as the active life immediately

        Returns:
            life_id: UUID for the created life

        Raises:
            ValueError: If a life with this name already exists for this user+persona
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Generate unique life_id
        life_id = str(uuid.uuid4())

        try:
            # If set_active, deactivate all other lives for this user+persona
            if set_active:
                cursor.execute(
                    """
                    UPDATE lives
                    SET is_active = 0
                    WHERE user_id = ? AND persona_id = ?
                """,
                    (user_id, persona_id),
                )

            # Insert new life
            cursor.execute(
                """
                INSERT INTO lives (life_id, user_id, persona_id, name, description, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    life_id,
                    user_id,
                    persona_id,
                    name,
                    description,
                    1 if set_active else 0,
                ),
            )

            conn.commit()
            return life_id

        except sqlite3.IntegrityError:
            raise ValueError(
                f"A life named '{name}' already exists for this user+persona pair"
            )
        finally:
            conn.close()

    def get_active_life(
        self, user_id: str, persona_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the currently active life for a user+persona pair.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Dict with life info, or None if no active life
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT life_id, name, description, created_at
            FROM lives
            WHERE user_id = ? AND persona_id = ? AND is_active = 1
        """,
            (user_id, persona_id),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "life_id": result["life_id"],
                "name": result["name"],
                "description": result["description"],
                "created_at": result["created_at"],
            }
        return None

    def switch_life(self, user_id: str, persona_id: str, life_name: str) -> bool:
        """
        Switch to a different life for this user+persona pair.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            life_name: Name of the life to switch to

        Returns:
            True if successful, False if life not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # First, deactivate all lives for this user+persona
        cursor.execute(
            """
            UPDATE lives
            SET is_active = 0
            WHERE user_id = ? AND persona_id = ?
        """,
            (user_id, persona_id),
        )

        # Then activate the target life
        cursor.execute(
            """
            UPDATE lives
            SET is_active = 1
            WHERE user_id = ? AND persona_id = ? AND name = ?
        """,
            (user_id, persona_id, life_name),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def list_lives(self, user_id: str, persona_id: str) -> List[Dict[str, Any]]:
        """
        List all lives for a user+persona pair.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            List of dicts with life info
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT life_id, name, description, created_at, is_active
            FROM lives
            WHERE user_id = ? AND persona_id = ?
            ORDER BY created_at DESC
        """,
            (user_id, persona_id),
        )

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "life_id": row["life_id"],
                "name": row["name"],
                "description": row["description"],
                "created_at": row["created_at"],
                "is_active": bool(row["is_active"]),
            }
            for row in results
        ]

    def delete_life(self, user_id: str, persona_id: str, life_name: str) -> bool:
        """
        Delete a life (and all associated messages/memories).

        WARNING: This is destructive! All messages in this timeline will be deleted.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            life_name: Name of the life to delete

        Returns:
            True if successful, False if life not found or is active
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if this is the active life
        cursor.execute(
            """
            SELECT is_active, life_id
            FROM lives
            WHERE user_id = ? AND persona_id = ? AND name = ?
        """,
            (user_id, persona_id, life_name),
        )

        result = cursor.fetchone()

        if not result:
            conn.close()
            return False

        if result["is_active"]:
            conn.close()
            raise ValueError(
                "Cannot delete the active life. Switch to another life first."
            )

        life_id = result["life_id"]

        # Delete the life
        cursor.execute(
            """
            DELETE FROM lives
            WHERE life_id = ?
        """,
            (life_id,),
        )

        conn.commit()
        conn.close()

        return True

    def get_life_by_name(
        self, user_id: str, persona_id: str, life_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a life by its name.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            life_name: Name of the life

        Returns:
            Dict with life info, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT life_id, name, description, created_at, is_active
            FROM lives
            WHERE user_id = ? AND persona_id = ? AND name = ?
        """,
            (user_id, persona_id, life_name),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "life_id": result["life_id"],
                "name": result["name"],
                "description": result["description"],
                "created_at": result["created_at"],
                "is_active": bool(result["is_active"]),
            }
        return None

    def ensure_default_life(self, user_id: str, persona_id: str) -> str:
        """
        Ensure a default life exists for a user+persona pair.
        If no lives exist, create one named "Main Timeline".

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            life_id of the active life (existing or newly created)
        """
        active_life = self.get_active_life(user_id, persona_id)

        if active_life:
            return active_life["life_id"]

        # No active life - check if any lives exist
        all_lives = self.list_lives(user_id, persona_id)

        if all_lives:
            # Lives exist but none active - activate the first one
            first_life = all_lives[0]
            self.switch_life(user_id, persona_id, first_life["name"])
            return first_life["life_id"]

        # No lives at all - create default
        life_id = self.create_life(
            user_id=user_id,
            persona_id=persona_id,
            name="Main Timeline",
            description="The original timeline",
            set_active=True,
        )

        return life_id
