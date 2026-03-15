"""
Metacognition Engine - Internal Thought Tracking for Project Myriad.

This module stores and retrieves the AI's private internal monologue that occurs
before each response. Thoughts are extracted from <thought>...</thought> tags
and stored per user+persona pair for continuity across turns.

ARCHITECTURE:
- Thoughts stored in SQLite database (data/myriad.db)
- One thought per turn, keyed by user_id + persona_id
- Previous thought injected into next turn's context for planning continuity
"""

import sqlite3
from datetime import datetime
from typing import Optional


class MetacognitionEngine:
    """
    Manages storage and retrieval of internal thoughts (hidden monologue).

    The AI generates thoughts wrapped in <thought>...</thought> tags before responding.
    These thoughts are private planning/evaluation that can optionally be shown to the user.
    """

    def __init__(self, db_path: str = "data/myriad.db"):
        """
        Initialize the Metacognition Engine.

        Args:
            db_path: Path to SQLite database for storing thoughts
        """
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create the internal_thoughts table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS internal_thoughts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                thought TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(user_id, persona_id)
            )
        """
        )

        conn.commit()
        conn.close()

    def save_thought(self, user_id: str, persona_id: str, thought: str) -> None:
        """
        Save an internal thought for a user+persona pair.

        Overwrites any previous thought (we only keep the most recent one).

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            thought: The extracted thought content
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO internal_thoughts (user_id, persona_id, thought, timestamp)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, persona_id) 
            DO UPDATE SET 
                thought = excluded.thought,
                timestamp = excluded.timestamp
        """,
            (user_id, persona_id, thought, datetime.now().isoformat()),
        )

        conn.commit()
        conn.close()

    def get_previous_thought(self, user_id: str, persona_id: str) -> Optional[str]:
        """
        Retrieve the most recent internal thought for a user+persona pair.

        This is used to inject the previous turn's thought into the next turn's context,
        maintaining continuity in the AI's internal planning.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            The previous thought content, or None if no thought exists
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT thought FROM internal_thoughts
            WHERE user_id = ? AND persona_id = ?
        """,
            (user_id, persona_id),
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def clear_thoughts(self, user_id: str, persona_id: Optional[str] = None) -> None:
        """
        Clear internal thoughts for a user.

        Args:
            user_id: User identifier
            persona_id: If provided, only clear thoughts for this persona.
                       If None, clear ALL thoughts for this user.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if persona_id:
            cursor.execute(
                "DELETE FROM internal_thoughts WHERE user_id = ? AND persona_id = ?",
                (user_id, persona_id),
            )
        else:
            cursor.execute(
                "DELETE FROM internal_thoughts WHERE user_id = ?", (user_id,)
            )

        conn.commit()
        conn.close()
