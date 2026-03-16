"""
Session Notes Manager - Short-term volatile context injection with TTL.

This module manages ephemeral short-term session notes with automatic expiration.
Notes are injected into the prompt context and automatically deleted after a specified
number of conversation turns.

Part of the Discretion Engine's memory routing system.
"""

import sqlite3
from typing import Optional, Tuple


class SessionNotesManager:
    """Manages short-term session notes with TTL (Time-To-Live) in conversation turns."""

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
        """Create session_notes table with TTL support."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_notes (
                user_id TEXT PRIMARY KEY,
                note_text TEXT NOT NULL,
                ttl_remaining INTEGER NOT NULL DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: Add ttl_remaining column if it doesn't exist
        cursor.execute("PRAGMA table_info(session_notes)")
        columns = [col[1] for col in cursor.fetchall()]
        if "ttl_remaining" not in columns:
            print("⚠ Migrating session_notes table: Adding ttl_remaining column...")
            cursor.execute(
                "ALTER TABLE session_notes ADD COLUMN ttl_remaining INTEGER NOT NULL DEFAULT 5"
            )
            print("✓ Migration complete")

        conn.commit()
        conn.close()

    def set_note(self, user_id: str, note_text: str, ttl_turns: int = 5) -> None:
        """
        Set or update a short-term session note with TTL.

        Args:
            user_id: User identifier
            note_text: The note text to inject into context
            ttl_turns: Number of conversation turns before auto-expiration (default: 5)
        """
        # Clamp TTL to reasonable range
        ttl_turns = max(1, min(20, ttl_turns))

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO session_notes (user_id, note_text, ttl_remaining, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET 
                note_text = excluded.note_text,
                ttl_remaining = excluded.ttl_remaining,
                updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, note_text, ttl_turns),
        )

        conn.commit()
        conn.close()

    def get_note(self, user_id: str) -> Optional[str]:
        """
        Get the current session note for a user (without TTL info).

        Args:
            user_id: User identifier

        Returns:
            Note text if exists, None otherwise
        """
        note_data = self.get_note_with_ttl(user_id)
        if note_data:
            return note_data[0]  # Return just the text
        return None

    def get_note_with_ttl(self, user_id: str) -> Optional[Tuple[str, int]]:
        """
        Get the current session note with TTL information.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (note_text, ttl_remaining) if exists, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT note_text, ttl_remaining FROM session_notes WHERE user_id = ?",
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return (row["note_text"], row["ttl_remaining"])
        return None

    def decrement_ttl(self, user_id: str) -> bool:
        """
        Decrement the TTL counter for a user's note. If TTL reaches 0, delete the note.

        This should be called after each AI response to track conversation turns.

        Args:
            user_id: User identifier

        Returns:
            True if note still exists after decrement, False if expired and deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current TTL
        cursor.execute(
            "SELECT ttl_remaining FROM session_notes WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False

        current_ttl = row["ttl_remaining"]

        if current_ttl <= 1:
            # TTL expired - delete the note
            cursor.execute("DELETE FROM session_notes WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return False
        else:
            # Decrement TTL
            cursor.execute(
                "UPDATE session_notes SET ttl_remaining = ttl_remaining - 1 WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
            conn.close()
            return True

    def clear_note(self, user_id: str) -> bool:
        """
        Clear the session note for a user (manual deletion).

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
