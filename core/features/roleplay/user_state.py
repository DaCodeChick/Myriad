"""
User state management for Project Myriad.

This module handles user-specific state including:
- Active persona tracking (both single and ensemble mode)
- Last interaction timestamps
- User session management

Part of RDSSC Phase 3: Enhanced with ensemble mode support.
"""

import sqlite3
import json
from typing import Optional, List
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
        Set the active persona for a user (clears all others - single persona mode).

        Args:
            user_id: User identifier
            persona: Persona ID to activate
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Update both legacy field and new ensemble field (as single-item array)
        persona_ids_json = json.dumps([persona])

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_persona, active_persona_ids, last_interaction_time)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                active_persona = excluded.active_persona,
                active_persona_ids = excluded.active_persona_ids,
                last_interaction_time = excluded.last_interaction_time
        """,
            (user_id, persona, persona_ids_json, datetime.now().isoformat()),
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

    # ========================
    # ENSEMBLE MODE SUPPORT
    # ========================

    def get_active_personas(self, user_id: str) -> List[str]:
        """
        Get all currently active personas for a user (Ensemble Mode).

        Args:
            user_id: User identifier

        Returns:
            List of persona_ids (empty list if none active)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT active_persona_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row or not row["active_persona_ids"]:
            return []

        try:
            return json.loads(row["active_persona_ids"])
        except (json.JSONDecodeError, TypeError):
            return []

    def add_active_persona(self, user_id: str, persona_id: str) -> None:
        """
        Add a persona to the active ensemble (appends to list).

        Args:
            user_id: User identifier
            persona_id: The persona to add
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current personas
        cursor.execute(
            "SELECT active_persona_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()

        current_personas = []
        if row and row["active_persona_ids"]:
            try:
                current_personas = json.loads(row["active_persona_ids"])
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
            user_id: User identifier
            persona_id: The persona to remove

        Returns:
            True if persona was removed, False if it wasn't active
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current personas
        cursor.execute(
            "SELECT active_persona_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()

        if not row or not row["active_persona_ids"]:
            conn.close()
            return False

        try:
            current_personas = json.loads(row["active_persona_ids"])
        except (json.JSONDecodeError, TypeError):
            conn.close()
            return False

        # Remove persona if present
        if persona_id not in current_personas:
            conn.close()
            return False

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

    def clear_active_personas(self, user_id: str) -> None:
        """
        Clear all active personas for a user.

        Args:
            user_id: User identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_state
            SET active_persona_ids = ?
            WHERE user_id = ?
        """,
            (json.dumps([]), user_id),
        )

        conn.commit()
        conn.close()
