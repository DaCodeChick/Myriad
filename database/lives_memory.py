"""
Timeline-scoped memory operations for Project Myriad's Lives system.

This module handles memory operations specific to the Lives (timeline branching) system:
- Cloning memories when creating timeline branches
- Deleting memories after checkpoints (for FORGET option)
- Managing memory consistency across timeline branches

Part of RDSSC Phase 5: Split memory_matrix.py into focused modules.
"""

import sqlite3
from typing import Optional


class LivesMemoryManager:
    """Manages memory operations for the Lives timeline system."""

    def __init__(self, db_path: str, vector_memory=None):
        """
        Initialize lives memory manager.

        Args:
            db_path: Path to SQLite database file
            vector_memory: Optional VectorMemory instance for vector store sync
        """
        self.db_path = db_path
        self.vector_memory = vector_memory
        self.vector_memory_enabled = vector_memory is not None

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def delete_memories_after_checkpoint(
        self, life_id: str, checkpoint_message_id: int
    ) -> int:
        """
        Delete all memories (SQL + vector) that occurred AFTER a checkpoint.
        Used when loading a save state with FORGET option.

        Args:
            life_id: The timeline ID
            checkpoint_message_id: Delete all memories with id > this value

        Returns:
            Number of memories deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # First, get the IDs of memories to delete (for vector cleanup)
        cursor.execute(
            """
            SELECT id
            FROM memories
            WHERE life_id = ? AND id > ?
        """,
            (life_id, checkpoint_message_id),
        )

        memory_ids = [str(row["id"]) for row in cursor.fetchall()]

        # Delete from SQL
        cursor.execute(
            """
            DELETE FROM memories
            WHERE life_id = ? AND id > ?
        """,
            (life_id, checkpoint_message_id),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        # Delete from vector memory
        if self.vector_memory_enabled and self.vector_memory and memory_ids:
            try:
                self.vector_memory.delete_memories_by_ids(memory_ids)
            except Exception as e:
                print(f"Warning: Failed to delete vectors: {e}")

        return deleted_count

    def clone_life_memories(
        self,
        source_life_id: str,
        target_life_id: str,
        up_to_message_id: Optional[int] = None,
    ) -> int:
        """
        Clone all memories from one life to another.
        Used when creating a branch before rewinding.

        Args:
            source_life_id: The life to copy from
            target_life_id: The life to copy to
            up_to_message_id: Optional - only clone up to this message ID

        Returns:
            Number of memories cloned
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if up_to_message_id:
            cursor.execute(
                """
                INSERT INTO memories (user_id, origin_persona, role, content, visibility_scope, life_id, timestamp)
                SELECT user_id, origin_persona, role, content, visibility_scope, ?, timestamp
                FROM memories
                WHERE life_id = ? AND id <= ?
                ORDER BY id ASC
            """,
                (target_life_id, source_life_id, up_to_message_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO memories (user_id, origin_persona, role, content, visibility_scope, life_id, timestamp)
                SELECT user_id, origin_persona, role, content, visibility_scope, ?, timestamp
                FROM memories
                WHERE life_id = ?
                ORDER BY id ASC
            """,
                (target_life_id, source_life_id),
            )

        cloned_count = cursor.rowcount
        conn.commit()

        # Now clone to vector memory
        if self.vector_memory_enabled and self.vector_memory:
            # Get the newly inserted memories
            cursor.execute(
                """
                SELECT id, role, content, user_id, origin_persona, visibility_scope, timestamp
                FROM memories
                WHERE life_id = ?
                ORDER BY id ASC
            """,
                (target_life_id,),
            )

            for row in cursor.fetchall():
                try:
                    self.vector_memory.add_memory(
                        memory_id=str(row["id"]),
                        user_id=row["user_id"],
                        origin_persona=row["origin_persona"],
                        role=row["role"],
                        content=row["content"],
                        visibility_scope=row["visibility_scope"],
                        life_id=target_life_id,
                        timestamp=row["timestamp"],
                    )
                except Exception as e:
                    print(f"Warning: Failed to clone vector memory {row['id']}: {e}")

        conn.close()
        return cloned_count
