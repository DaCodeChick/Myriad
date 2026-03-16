"""
Session Notes Manager - Silent meta-level context injection system.

This module manages ephemeral session notes that users can inject into the
prompt context without generating a public response. Notes are stored per-user
and are automatically injected near the end of the context window during
prompt building.

Unlike /dm (active narrator), /note is completely silent and meta-level.
"""

import sqlite3
from typing import Optional


class SessionNotesManager:
    """Manages ephemeral session notes for meta-level context injection."""

    def __init__(self, db_path: str = "data/myriad_state.db"):
        """
        Initialize the session notes manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Create session_notes table if it doesn't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_notes (
                user_id TEXT PRIMARY KEY,
                note_text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def set_note(self, user_id: str, note_text: str) -> None:
        """
        Set or update a session note for a user.

        Args:
            user_id: User identifier
            note_text: The note text to inject into context
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO session_notes (user_id, note_text, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET 
                note_text = excluded.note_text,
                updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, note_text),
        )

        conn.commit()
        conn.close()

    def get_note(self, user_id: str) -> Optional[str]:
        """
        Get the current session note for a user.

        Args:
            user_id: User identifier

        Returns:
            Note text if exists, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT note_text FROM session_notes WHERE user_id = ?", (user_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return row["note_text"]
        return None

    def clear_note(self, user_id: str) -> bool:
        """
        Clear the session note for a user.

        Args:
            user_id: User identifier

        Returns:
            True if a note was cleared, False if no note existed
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM session_notes WHERE user_id = ?", (user_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def has_note(self, user_id: str) -> bool:
        """
        Check if a user has an active session note.

        Args:
            user_id: User identifier

        Returns:
            True if user has a note, False otherwise
        """
        return self.get_note(user_id) is not None
