"""
User Mask (Persona) System for Project Myriad.

This module is a thin wrapper around PersonaLoader that manages which persona
a user is currently "wearing" as their character identity. User masks are just
regular personas stored in personas/user_masks/ - they can be worn by users
or used as AI personas interchangeably.

When a user wears a mask, the AI persona will interact with them as that character.
The AI-specific parameters (temperature, max_tokens, etc.) are simply ignored when
the persona is worn by a user.

ENSEMBLE MODE: Supports multiple active masks simultaneously (user can wear multiple characters).
"""

import sqlite3
import json
from typing import Optional, List
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
                active_persona_ids TEXT,
                active_mask_ids TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Migrate old single-value columns to JSON arrays if they exist
        cursor.execute("PRAGMA table_info(user_state)")
        columns = {row[1]: row for row in cursor.fetchall()}

        # Check if we need to migrate from old schema
        if "active_persona_id" in columns and "active_persona_ids" not in columns:
            # Migrate active_persona_id to active_persona_ids
            cursor.execute("ALTER TABLE user_state ADD COLUMN active_persona_ids TEXT")
            cursor.execute(
                """
                UPDATE user_state 
                SET active_persona_ids = json_array(active_persona_id) 
                WHERE active_persona_id IS NOT NULL AND active_persona_id != ''
                """
            )
            # Don't drop the old column yet for backwards compatibility

        if "active_mask_id" in columns and "active_mask_ids" not in columns:
            # Migrate active_mask_id to active_mask_ids
            cursor.execute("ALTER TABLE user_state ADD COLUMN active_mask_ids TEXT")
            cursor.execute(
                """
                UPDATE user_state 
                SET active_mask_ids = json_array(active_mask_id) 
                WHERE active_mask_id IS NOT NULL AND active_mask_id != ''
                """
            )
            # Don't drop the old column yet for backwards compatibility

        # Add new columns if they don't exist
        cursor.execute("PRAGMA table_info(user_state)")
        columns = {row[1]: row for row in cursor.fetchall()}

        if "active_persona_ids" not in columns:
            cursor.execute("ALTER TABLE user_state ADD COLUMN active_persona_ids TEXT")

        if "active_mask_ids" not in columns:
            cursor.execute("ALTER TABLE user_state ADD COLUMN active_mask_ids TEXT")

        conn.commit()
        conn.close()

    def add_active_mask(self, user_id: str, persona_id: str) -> None:
        """
        Add a mask to the user's active ensemble (appends to list).

        Args:
            user_id: User identifier
            persona_id: Persona ID to add (e.g., "user_masks/schala")
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current masks
        cursor.execute(
            "SELECT active_mask_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()

        current_masks = []
        if row and row["active_mask_ids"]:
            try:
                current_masks = json.loads(row["active_mask_ids"])
            except (json.JSONDecodeError, TypeError):
                current_masks = []

        # Add new mask if not already in list
        if persona_id not in current_masks:
            current_masks.append(persona_id)

        # Update database
        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_mask_ids)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_mask_ids = excluded.active_mask_ids
        """,
            (user_id, json.dumps(current_masks)),
        )

        conn.commit()
        conn.close()

    def remove_active_mask(self, user_id: str, persona_id: str) -> bool:
        """
        Remove a specific mask from the user's active ensemble.

        Args:
            user_id: User identifier
            persona_id: Persona ID to remove

        Returns:
            True if mask was removed, False if it wasn't in the list
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current masks
        cursor.execute(
            "SELECT active_mask_ids FROM user_state WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()

        if not row or not row["active_mask_ids"]:
            conn.close()
            return False

        try:
            current_masks = json.loads(row["active_mask_ids"])
        except (json.JSONDecodeError, TypeError):
            conn.close()
            return False

        # Remove mask if present
        if persona_id in current_masks:
            current_masks.remove(persona_id)

            # Update database
            cursor.execute(
                """
                UPDATE user_state 
                SET active_mask_ids = ? 
                WHERE user_id = ?
            """,
                (json.dumps(current_masks), user_id),
            )

            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    def clear_active_masks(self, user_id: str) -> None:
        """
        Clear all active masks for a user.

        Args:
            user_id: User identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_state 
            SET active_mask_ids = NULL 
            WHERE user_id = ?
        """,
            (user_id,),
        )

        conn.commit()
        conn.close()

    def set_active_mask(self, user_id: str, persona_id: Optional[str]) -> None:
        """
        Set a single active mask (legacy method - clears other masks).

        Args:
            user_id: User identifier
            persona_id: Persona ID to wear (e.g., "user_masks/schala"), or None to clear
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        mask_ids = None
        if persona_id:
            mask_ids = json.dumps([persona_id])

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_mask_ids)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_mask_ids = excluded.active_mask_ids
        """,
            (user_id, mask_ids),
        )

        conn.commit()
        conn.close()

    def get_active_masks(self, user_id: str) -> List[PersonaCartridge]:
        """
        Get all currently active masks (personas) for a user.

        Args:
            user_id: User identifier

        Returns:
            List of PersonaCartridge objects (empty list if none active)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT active_mask_ids FROM user_state WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row or not row["active_mask_ids"]:
            return []

        try:
            mask_ids = json.loads(row["active_mask_ids"])
        except (json.JSONDecodeError, TypeError):
            return []

        # Load all masks
        masks = []
        for mask_id in mask_ids:
            mask = self.persona_loader.load_persona(mask_id)
            if mask:
                masks.append(mask)

        return masks

    def get_active_mask(self, user_id: str) -> Optional[PersonaCartridge]:
        """
        Get the first active mask (legacy method for backwards compatibility).

        Args:
            user_id: User identifier

        Returns:
            First PersonaCartridge if user has an active mask, None otherwise
        """
        masks = self.get_active_masks(user_id)
        return masks[0] if masks else None
