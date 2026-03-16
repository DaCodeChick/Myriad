"""
Scenario appearance caching and database operations.

This module handles SQLite operations for caching AI-generated appearance descriptions
and tracking active scenarios per user.
"""

import sqlite3
from typing import Optional


class ScenarioCache:
    """Manages SQLite caching for scenario appearances and active scenarios."""

    def __init__(self, db_path: str):
        """
        Initialize scenario cache.

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
        """Ensure cached appearance and active scenario tables exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create table for storing cached appearances (AI-generated visual descriptions)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_appearances (
                scenario_name TEXT PRIMARY KEY,
                cached_appearance TEXT,
                last_generated TEXT DEFAULT CURRENT_TIMESTAMP,
                image_hashes TEXT
            )
        """
        )

        # Add active_scenario_name column to user_state if it doesn't exist
        cursor.execute("PRAGMA table_info(user_state)")
        columns = [row[1] for row in cursor.fetchall()]

        if "active_scenario_name" not in columns:
            cursor.execute(
                """
                ALTER TABLE user_state 
                ADD COLUMN active_scenario_name TEXT
            """
            )

        conn.commit()
        conn.close()

    def get_cached_appearance(self, scenario_name: str) -> Optional[tuple]:
        """
        Get cached appearance and image hash for a scenario.

        Args:
            scenario_name: Name of the scenario

        Returns:
            Tuple of (cached_appearance, image_hashes) if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cached_appearance, image_hashes 
            FROM scenario_appearances 
            WHERE scenario_name = ?
        """,
            (scenario_name,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return (row["cached_appearance"], row["image_hashes"])
        return None

    def store_cached_appearance(
        self, scenario_name: str, appearance: str, image_hash: str
    ) -> None:
        """
        Store cached appearance in database.

        Args:
            scenario_name: Name of the scenario
            appearance: AI-generated appearance description
            image_hash: Hash of images used to generate the appearance
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO scenario_appearances
            (scenario_name, cached_appearance, image_hashes, last_generated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (scenario_name, appearance, image_hash),
        )

        conn.commit()
        conn.close()

    def update_appearance_only(
        self, scenario_name: str, cached_appearance: Optional[str]
    ) -> None:
        """
        Update only the cached_appearance field (used by manual updates).

        Args:
            scenario_name: Name of the scenario
            cached_appearance: New appearance description, or None to clear
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO scenario_appearances (scenario_name, cached_appearance)
            VALUES (?, ?)
            ON CONFLICT(scenario_name) DO UPDATE SET 
                cached_appearance = excluded.cached_appearance,
                last_generated = CURRENT_TIMESTAMP
        """,
            (scenario_name, cached_appearance),
        )

        conn.commit()
        conn.close()

    def delete_cached_appearance(self, scenario_name: str) -> None:
        """
        Delete cached appearance from database.

        Args:
            scenario_name: Name of the scenario
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM scenario_appearances WHERE scenario_name = ?",
            (scenario_name,),
        )
        conn.commit()
        conn.close()

    def set_active_scenario(self, user_id: str, scenario_name: Optional[str]) -> None:
        """
        Set the active scenario for a user.

        Args:
            user_id: User identifier
            scenario_name: Name of the scenario to activate, or None to clear
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_scenario_name)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_scenario_name = excluded.active_scenario_name
        """,
            (user_id, scenario_name),
        )

        conn.commit()
        conn.close()

    def get_active_scenario_name(self, user_id: str) -> Optional[str]:
        """
        Get the currently active scenario name for a user.

        Args:
            user_id: User identifier

        Returns:
            Scenario name if user has an active scenario, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT active_scenario_name FROM user_state WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row and row["active_scenario_name"]:
            return row["active_scenario_name"]

        return None
