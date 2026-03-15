"""
SQLite-based caching layer for persona appearances.

Manages the database schema and operations for storing cached appearance
descriptions with image hashes to detect when regeneration is needed.
"""

import sqlite3
from typing import Optional, Tuple


class PersonaCache:
    """SQLite-based cache for persona appearances."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the persona cache.

        Args:
            db_path: Path to SQLite database for cached appearances
        """
        self.db_path = db_path

        if self.db_path:
            self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure persona_appearances table exists in the database."""
        if not self.db_path:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS persona_appearances (
                persona_id TEXT PRIMARY KEY,
                cached_appearance TEXT,
                last_generated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_hashes TEXT
            )
            """
        )

        conn.commit()
        conn.close()

    def get_cached_appearance(self, persona_id: str) -> Optional[Tuple[str, str]]:
        """
        Retrieve cached appearance and image hashes from database.

        Args:
            persona_id: The persona ID to look up

        Returns:
            Tuple of (cached_appearance, image_hashes) if found, None otherwise
        """
        if not self.db_path:
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cached_appearance, image_hashes
            FROM persona_appearances
            WHERE persona_id = ?
            """,
            (persona_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return (row[0], row[1])
        return None

    def store_cached_appearance(
        self, persona_id: str, appearance: str, image_hash: str
    ) -> None:
        """
        Store cached appearance in database.

        Args:
            persona_id: The persona ID
            appearance: The generated appearance description
            image_hash: Hash of the images used to generate the appearance
        """
        if not self.db_path:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO persona_appearances
            (persona_id, cached_appearance, image_hashes, last_generated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (persona_id, appearance, image_hash),
        )

        conn.commit()
        conn.close()

    def update_appearance(
        self, persona_id: str, cached_appearance: Optional[str]
    ) -> bool:
        """
        Update or clear the cached appearance for a persona.

        Args:
            persona_id: The persona ID
            cached_appearance: New appearance description, or None to clear

        Returns:
            True if successful, False otherwise
        """
        if not self.db_path:
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if cached_appearance:
                # Store new appearance
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO persona_appearances
                    (persona_id, cached_appearance, image_hashes, last_generated)
                    VALUES (?, ?, '', CURRENT_TIMESTAMP)
                    """,
                    (persona_id, cached_appearance),
                )
            else:
                # Clear appearance
                cursor.execute(
                    "DELETE FROM persona_appearances WHERE persona_id = ?",
                    (persona_id,),
                )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error updating persona appearance '{persona_id}': {e}")
            return False

    def delete_appearance(self, persona_id: str) -> None:
        """
        Delete cached appearance for a persona (forces regeneration).

        Args:
            persona_id: The persona ID
        """
        if not self.db_path:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM persona_appearances WHERE persona_id = ?",
            (persona_id,),
        )

        conn.commit()
        conn.close()
