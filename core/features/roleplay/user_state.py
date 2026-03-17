"""
User state management for Project Myriad.

This module handles user-specific state including:
- Active persona tracking
- Last interaction timestamps
- User session management

Part of RDSSC Phase 5: Split memory_matrix.py into focused modules.
"""

import sqlite3
from typing import Optional
from datetime import datetime


class UserStateManager:
    """Manages user state including active personas and interaction timestamps."""

    def __init__(self, db_path: str):
        """
        Initialize user state manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Ensure user_state table exists with compatible schema.

        RDSSC Phase 1: Use same schema as user_masks.py to avoid conflicts.
        Both modules share the same table, so we need compatible schemas.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Use the same schema as user_masks.py (ensemble-compatible)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_state (
                user_id TEXT PRIMARY KEY,
                active_persona TEXT,
                last_interaction_time TEXT,
                active_persona_ids TEXT,
                active_mask_ids TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def get_active_persona(self, user_id: str) -> Optional[str]:
        """
        Get the active persona for a user.

        Args:
            user_id: User identifier

        Returns:
            Active persona name or None if not set
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT active_persona FROM user_state WHERE user_id = ?", (user_id,)
        )

        row = cursor.fetchone()
        conn.close()

        return row["active_persona"] if row else None

    def set_active_persona(self, user_id: str, persona: str) -> None:
        """
        Set the active persona for a user.

        Args:
            user_id: User identifier
            persona: Persona name to activate
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_persona, last_interaction_time)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_persona = excluded.active_persona
        """,
            (user_id, persona, datetime.now().isoformat()),
        )

        conn.commit()
        conn.close()

    def update_last_interaction(self, user_id: str) -> None:
        """
        Update the last interaction timestamp for a user.

        Args:
            user_id: User identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, last_interaction_time)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_interaction_time = excluded.last_interaction_time
        """,
            (user_id, datetime.now().isoformat()),
        )

        conn.commit()
        conn.close()

    def get_last_interaction(self, user_id: str) -> Optional[datetime]:
        """
        Get the last interaction timestamp for a user.

        Args:
            user_id: User identifier

        Returns:
            Last interaction datetime or None if never interacted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT last_interaction_time FROM user_state WHERE user_id = ?", (user_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if row and row["last_interaction_time"]:
            return datetime.fromisoformat(row["last_interaction_time"])
        return None
