"""
User Mask (Persona) System for Project Myriad.

This module allows users to create and wear different character personas (masks)
that the AI will recognize and respond to, enabling rich roleplay scenarios.

A "mask" is a user-side persona that defines who the user is presenting as
during the conversation, including:
- Name (e.g., "Captain Sarah Chen")
- Description (brief character identity)
- Background (detailed lore and history)

When a user wears a mask, the AI persona will interact with them as that character.
"""

import sqlite3
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class UserMask:
    """Represents a user persona/mask."""

    mask_id: int
    user_id: str
    name: str
    description: str
    background: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert mask to dictionary format."""
        return {
            "mask_id": self.mask_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "background": self.background,
        }


class UserMaskManager:
    """Manages user-created personas (masks) for roleplay."""

    def __init__(self, db_path: str):
        """
        Initialize user mask manager.

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
        """Ensure user masks tables exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create user_personas table for storing masks
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                background TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        """
        )

        # Add active_mask_id column to user_state if it doesn't exist
        # First check if the column already exists
        cursor.execute("PRAGMA table_info(user_state)")
        columns = [row[1] for row in cursor.fetchall()]

        if "active_mask_id" not in columns:
            cursor.execute(
                """
                ALTER TABLE user_state 
                ADD COLUMN active_mask_id INTEGER
            """
            )

        conn.commit()
        conn.close()

    def create_mask(
        self,
        user_id: str,
        name: str,
        description: str,
        background: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create a new user mask/persona.

        Args:
            user_id: User identifier
            name: Name of the character persona
            description: Brief character description/identity
            background: Optional detailed background/lore

        Returns:
            The mask_id of the created mask, or None if creation failed
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO user_personas (user_id, name, description, background)
                VALUES (?, ?, ?, ?)
            """,
                (user_id, name, description, background),
            )

            mask_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return mask_id

        except sqlite3.IntegrityError:
            # Mask with this name already exists for this user
            conn.close()
            return None

    def get_mask(self, user_id: str, name: str) -> Optional[UserMask]:
        """
        Get a mask by name for a specific user.

        Args:
            user_id: User identifier
            name: Name of the mask

        Returns:
            UserMask if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, name, description, background
            FROM user_personas
            WHERE user_id = ? AND name = ?
        """,
            (user_id, name),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return UserMask(
                mask_id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row["description"],
                background=row["background"],
            )

        return None

    def get_mask_by_id(self, mask_id: int) -> Optional[UserMask]:
        """
        Get a mask by its ID.

        Args:
            mask_id: Unique mask identifier

        Returns:
            UserMask if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, name, description, background
            FROM user_personas
            WHERE id = ?
        """,
            (mask_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return UserMask(
                mask_id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row["description"],
                background=row["background"],
            )

        return None

    def list_user_masks(self, user_id: str) -> List[UserMask]:
        """
        List all masks for a specific user.

        Args:
            user_id: User identifier

        Returns:
            List of UserMask objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, name, description, background
            FROM user_personas
            WHERE user_id = ?
            ORDER BY name
        """,
            (user_id,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            UserMask(
                mask_id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row["description"],
                background=row["background"],
            )
            for row in rows
        ]

    def delete_mask(self, user_id: str, name: str) -> bool:
        """
        Delete a mask.

        Args:
            user_id: User identifier
            name: Name of the mask to delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM user_personas
            WHERE user_id = ? AND name = ?
        """,
            (user_id, name),
        )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def set_active_mask(self, user_id: str, mask_id: Optional[int]) -> None:
        """
        Set the active mask for a user.

        Args:
            user_id: User identifier
            mask_id: ID of the mask to activate, or None to clear
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_mask_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_mask_id = excluded.active_mask_id
        """,
            (user_id, mask_id),
        )

        conn.commit()
        conn.close()

    def get_active_mask(self, user_id: str) -> Optional[UserMask]:
        """
        Get the currently active mask for a user.

        Args:
            user_id: User identifier

        Returns:
            UserMask if user has an active mask, None otherwise
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
            return self.get_mask_by_id(row["active_mask_id"])

        return None

    def update_mask(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        background: Optional[str] = None,
    ) -> bool:
        """
        Update an existing mask.

        Args:
            user_id: User identifier
            name: Name of the mask to update
            description: New description (if provided)
            background: New background (if provided)

        Returns:
            True if updated, False if mask not found
        """
        mask = self.get_mask(user_id, name)
        if not mask:
            return False

        conn = self._get_connection()
        cursor = conn.cursor()

        # Build dynamic update query
        updates = []
        params = []

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if background is not None:
            updates.append("background = ?")
            params.append(background)

        if not updates:
            conn.close()
            return True  # Nothing to update

        params.extend([user_id, name])
        query = f"""
            UPDATE user_personas
            SET {", ".join(updates)}
            WHERE user_id = ? AND name = ?
        """

        cursor.execute(query, params)
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return updated
