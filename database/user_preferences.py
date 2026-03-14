"""
User Preferences - Per-user configuration for experimental features.

This module manages user-specific toggles for advanced Project Myriad features,
allowing each user to customize their experience independently.

Part of Project Myriad's configurable feature system.
"""

import sqlite3
from typing import Dict, Optional, Union


class UserPreferences:
    """Manages per-user configuration for experimental features."""

    def __init__(self, db_path: str = "data/myriad_state.db"):
        """
        Initialize the user preferences manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create the user_preferences table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                limbic_enabled INTEGER DEFAULT 1,
                cadence_degrader_enabled INTEGER DEFAULT 1,
                metacognition_enabled INTEGER DEFAULT 1,
                show_thoughts_inline INTEGER DEFAULT 0,
                autonomy_enabled INTEGER DEFAULT 1,
                autonomy_inactivity_hours REAL DEFAULT 4.0,
                autonomy_sleep_threshold REAL DEFAULT 0.2
            )
        """
        )

        conn.commit()
        conn.close()

    def get_preferences(self, user_id: str) -> Dict[str, Union[bool, float]]:
        """
        Get all preferences for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of preference flags (booleans and floats)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT limbic_enabled, cadence_degrader_enabled, metacognition_enabled,
                   show_thoughts_inline, autonomy_enabled, autonomy_inactivity_hours,
                   autonomy_sleep_threshold
            FROM user_preferences
            WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "limbic_enabled": bool(row[0]),
                "cadence_degrader_enabled": bool(row[1]),
                "metacognition_enabled": bool(row[2]),
                "show_thoughts_inline": bool(row[3]),
                "autonomy_enabled": bool(row[4]),
                "autonomy_inactivity_hours": float(row[5]),
                "autonomy_sleep_threshold": float(row[6]),
            }
        else:
            # Return defaults if no preferences found
            return {
                "limbic_enabled": True,
                "cadence_degrader_enabled": True,
                "metacognition_enabled": True,
                "show_thoughts_inline": False,
                "autonomy_enabled": True,
                "autonomy_inactivity_hours": 4.0,
                "autonomy_sleep_threshold": 0.2,
            }

    def get_preference(self, user_id: str, preference_name: str) -> Union[bool, float]:
        """
        Get a specific preference for a user.

        Args:
            user_id: User identifier
            preference_name: Name of preference flag

        Returns:
            Boolean or float value of the preference
        """
        prefs = self.get_preferences(user_id)

        # Default values based on type
        defaults = {
            "limbic_enabled": True,
            "cadence_degrader_enabled": True,
            "metacognition_enabled": True,
            "show_thoughts_inline": False,
            "autonomy_enabled": True,
            "autonomy_inactivity_hours": 4.0,
            "autonomy_sleep_threshold": 0.2,
        }

        return prefs.get(preference_name, defaults.get(preference_name, True))

    def set_preference(
        self, user_id: str, preference_name: str, value: Union[bool, float]
    ):
        """
        Set a specific preference for a user.

        Args:
            user_id: User identifier
            preference_name: Name of preference flag
            value: Boolean or float value to set
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Validate preference name
        valid_preferences = [
            "limbic_enabled",
            "cadence_degrader_enabled",
            "metacognition_enabled",
            "show_thoughts_inline",
            "autonomy_enabled",
            "autonomy_inactivity_hours",
            "autonomy_sleep_threshold",
        ]

        if preference_name not in valid_preferences:
            conn.close()
            raise ValueError(f"Invalid preference name: {preference_name}")

        # Convert boolean to int for storage, keep floats as-is
        stored_value = int(value) if isinstance(value, bool) else value

        # Insert or update preference
        cursor.execute(
            f"""
            INSERT INTO user_preferences (user_id, {preference_name})
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET {preference_name} = ?
        """,
            (user_id, stored_value, stored_value),
        )

        conn.commit()
        conn.close()

    def toggle_preference(self, user_id: str, preference_name: str) -> bool:
        """
        Toggle a specific preference for a user.

        Args:
            user_id: User identifier
            preference_name: Name of preference flag

        Returns:
            New boolean value after toggle
        """
        current_value = self.get_preference(user_id, preference_name)
        new_value = not current_value
        self.set_preference(user_id, preference_name, new_value)
        return new_value

    def reset_preferences(self, user_id: str):
        """
        Reset all preferences to defaults for a user.

        Args:
            user_id: User identifier
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM user_preferences
            WHERE user_id = ?
        """,
            (user_id,),
        )

        conn.commit()
        conn.close()

    def get_all_users_with_preference(self, preference_name: str, value: bool) -> list:
        """
        Get all users with a specific preference value.

        Useful for filtering (e.g., only users with autonomy enabled).

        Args:
            preference_name: Name of preference flag
            value: Boolean value to filter by

        Returns:
            List of user IDs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get users with explicit preference set
        cursor.execute(
            f"""
            SELECT user_id FROM user_preferences
            WHERE {preference_name} = ?
        """,
            (int(value),),
        )

        users = [row[0] for row in cursor.fetchall()]
        conn.close()

        return users
