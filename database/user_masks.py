"""
User Mask (Persona) System for Project Myriad.

This module is a thin wrapper around PersonaLoader that manages which persona
a user is currently "wearing" as their character identity. User masks are just
regular personas stored in personas/user_masks/ - they can be worn by users
or used as AI personas interchangeably.

When a user wears a mask, the AI persona will interact with them as that character.
The AI-specific parameters (temperature, max_tokens, etc.) are simply ignored when
the persona is worn by a user.
"""

import sqlite3
from typing import Optional
from core.persona_loader import PersonaLoader, PersonaCartridge


class UserMaskManager:
    """Manages which persona a user is currently wearing as their identity."""

    def __init__(self, db_path: str, persona_loader: PersonaLoader):
        """
        Initialize user mask manager.

        Args:
            db_path: Path to SQLite database file (for tracking active masks)
            persona_loader: The PersonaLoader instance to use for loading mask personas
        """
        self.db_path = db_path
        self.persona_loader = persona_loader
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Ensure active mask tracking exists in user_state table."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create user_state table if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_state (
                user_id TEXT PRIMARY KEY,
                active_persona_id TEXT,
                active_mask_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Add active_mask_id column to user_state if it doesn't exist
        cursor.execute("PRAGMA table_info(user_state)")
        columns = [row[1] for row in cursor.fetchall()]

        if "active_mask_id" not in columns:
            cursor.execute(
                """
                ALTER TABLE user_state 
                ADD COLUMN active_mask_id TEXT
            """
            )

        conn.commit()
        conn.close()

    def set_active_mask(self, user_id: str, persona_id: Optional[str]) -> None:
        """
        Set the active mask (persona) for a user.

        Args:
            user_id: User identifier
            persona_id: Persona ID to wear (e.g., "user_masks/schala"), or None to clear
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_mask_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_mask_id = excluded.active_mask_id
        """,
            (user_id, persona_id),
        )

        conn.commit()
        conn.close()

    def get_active_mask(self, user_id: str) -> Optional[PersonaCartridge]:
        """
        Get the currently active mask (persona) for a user.

        Args:
            user_id: User identifier

        Returns:
            PersonaCartridge if user has an active mask, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT active_mask_id FROM user_state WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row and row["active_mask_id"]:
            return self.persona_loader.load_persona(row["active_mask_id"])

        return None
