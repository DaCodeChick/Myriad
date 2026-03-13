"""
Save States Engine - Memory Checkpoint System for Project Myriad.

This module implements the "Memories" system - allowing users to save checkpoints
within a timeline and rewind back to them. Think of it like save states in an RPG
or visual novel.

Architecture:
- Save states are scoped to a specific life_id (timeline)
- Each save state captures a specific message_id (checkpoint)
- When loading a save state, user chooses: FORGET future or BRANCH to new timeline
- FORGET: Permanently delete all messages after the checkpoint
- BRANCH: Clone current timeline to new life, then rewind original

Database Schema:
    save_states (
        save_id TEXT PRIMARY KEY,
        life_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        checkpoint_message_id INTEGER NOT NULL,
        created_at TIMESTAMP,
        UNIQUE(life_id, name),
        FOREIGN KEY (life_id) REFERENCES lives(life_id),
        FOREIGN KEY (checkpoint_message_id) REFERENCES memories(id)
    )
"""

import sqlite3
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime


class SaveStatesEngine:
    """Manages save states (memory checkpoints) for timelines."""

    def __init__(self, db_path: str = "data/myriad_state.db"):
        """
        Initialize the Save States Engine.

        Args:
            db_path: Path to SQLite database (shared with MemoryMatrix and LivesEngine)
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
        """Create save_states table if it doesn't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS save_states (
                save_id TEXT PRIMARY KEY,
                life_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                checkpoint_message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(life_id, name),
                FOREIGN KEY (life_id) REFERENCES lives(life_id) ON DELETE CASCADE
            )
        """)

        # Create index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_save_states_life
            ON save_states(life_id)
        """)

        conn.commit()
        conn.close()

    # ========================
    # SAVE STATE MANAGEMENT
    # ========================

    def create_save_state(
        self,
        life_id: str,
        name: str,
        checkpoint_message_id: int,
        description: Optional[str] = None,
    ) -> str:
        """
        Create a new save state (checkpoint) for a timeline.

        Args:
            life_id: The timeline this save belongs to
            name: Name for this save state
            checkpoint_message_id: The message ID to save at (from memories table)
            description: Optional description

        Returns:
            save_id: UUID for the created save state

        Raises:
            ValueError: If a save with this name already exists in this life
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Generate unique save_id
        save_id = str(uuid.uuid4())

        try:
            cursor.execute(
                """
                INSERT INTO save_states (save_id, life_id, name, description, checkpoint_message_id)
                VALUES (?, ?, ?, ?, ?)
            """,
                (save_id, life_id, name, description, checkpoint_message_id),
            )

            conn.commit()
            return save_id

        except sqlite3.IntegrityError:
            raise ValueError(
                f"A save state named '{name}' already exists in this timeline"
            )
        finally:
            conn.close()

    def get_save_state(self, life_id: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a save state by name within a timeline.

        Args:
            life_id: The timeline ID
            name: Name of the save state

        Returns:
            Dict with save state info, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT save_id, name, description, checkpoint_message_id, created_at
            FROM save_states
            WHERE life_id = ? AND name = ?
        """,
            (life_id, name),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "save_id": result["save_id"],
                "name": result["name"],
                "description": result["description"],
                "checkpoint_message_id": result["checkpoint_message_id"],
                "created_at": result["created_at"],
            }
        return None

    def list_save_states(self, life_id: str) -> List[Dict[str, Any]]:
        """
        List all save states for a timeline.

        Args:
            life_id: The timeline ID

        Returns:
            List of dicts with save state info
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT save_id, name, description, checkpoint_message_id, created_at
            FROM save_states
            WHERE life_id = ?
            ORDER BY created_at DESC
        """,
            (life_id,),
        )

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "save_id": row["save_id"],
                "name": row["name"],
                "description": row["description"],
                "checkpoint_message_id": row["checkpoint_message_id"],
                "created_at": row["created_at"],
            }
            for row in results
        ]

    def delete_save_state(self, life_id: str, name: str) -> bool:
        """
        Delete a save state.

        Args:
            life_id: The timeline ID
            name: Name of the save state to delete

        Returns:
            True if successful, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM save_states
            WHERE life_id = ? AND name = ?
        """,
            (life_id, name),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def get_latest_message_id(self, life_id: str) -> Optional[int]:
        """
        Get the most recent message ID for a timeline.
        Used when creating a save state at "current moment".

        Args:
            life_id: The timeline ID

        Returns:
            message_id or None if no messages exist
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id
            FROM memories
            WHERE life_id = ?
            ORDER BY id DESC
            LIMIT 1
        """,
            (life_id,),
        )

        result = cursor.fetchone()
        conn.close()

        return result["id"] if result else None

    def count_messages_after_checkpoint(
        self, life_id: str, checkpoint_message_id: int
    ) -> int:
        """
        Count how many messages exist after a checkpoint.
        Used to warn user before destructive operations.

        Args:
            life_id: The timeline ID
            checkpoint_message_id: The checkpoint message ID

        Returns:
            Number of messages that would be deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM memories
            WHERE life_id = ? AND id > ?
        """,
            (life_id, checkpoint_message_id),
        )

        result = cursor.fetchone()
        conn.close()

        return result["count"] if result else 0
