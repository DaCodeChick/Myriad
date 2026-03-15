"""
User Preferences - Per-user configuration for experimental features.

This module manages user-specific toggles for advanced Project Myriad features,
allowing each user to customize their experience independently.

Part of Project Myriad's configurable feature system.
"""

import sqlite3
from typing import Dict, Literal, Optional, Union

# Type alias for memory visibility modes
MemoryVisibility = Literal["GLOBAL", "USER_SHARED", "ISOLATED"]


class UserPreferences:
    """Manages per-user configuration for experimental features."""

    def __init__(self, db_path: str = "data/myriad.db"):
        """
        Initialize the user preferences manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Create the user_preferences table if it doesn't exist, and migrate schema if needed."""
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
                autonomy_sleep_threshold REAL DEFAULT 0.2,
                default_memory_visibility TEXT DEFAULT 'ISOLATED',
                lives_enabled INTEGER DEFAULT 1,
                universal_rules_enabled INTEGER DEFAULT 1
            )
        """
        )

        # Migration: Add new columns if they don't exist (for existing databases)
        cursor.execute("PRAGMA table_info(user_preferences)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if "lives_enabled" not in existing_columns:
            cursor.execute(
                "ALTER TABLE user_preferences ADD COLUMN lives_enabled INTEGER DEFAULT 1"
            )

        if "universal_rules_enabled" not in existing_columns:
            cursor.execute(
                "ALTER TABLE user_preferences ADD COLUMN universal_rules_enabled INTEGER DEFAULT 1"
            )

        # Degradation Profiles Table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS degradation_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                persona_id TEXT,
                profile_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                
                vowel_stretch_enabled INTEGER DEFAULT 1,
                panic_effects_enabled INTEGER DEFAULT 1,
                sedation_effects_enabled INTEGER DEFAULT 1,
                
                vowel_stretch_base_chance REAL DEFAULT 0.01,
                vowel_stretch_scale_factor REAL DEFAULT 0.057,
                vowel_stretch_min_word_length INTEGER DEFAULT 4,
                vowel_stretch_max_repeats INTEGER DEFAULT 2,
                
                panic_stutter_base_chance REAL DEFAULT 0.05,
                panic_stutter_scale_factor REAL DEFAULT 0.10,
                panic_caps_base_chance REAL DEFAULT 0.03,
                panic_caps_scale_factor REAL DEFAULT 0.07,
                panic_min_word_length INTEGER DEFAULT 3,
                
                sedation_ellipsis_chance REAL DEFAULT 0.3,
                
                UNIQUE(user_id, persona_id, profile_name)
            )
        """
        )

        # Insert default system presets if they don't exist
        from datetime import datetime

        now = datetime.utcnow().isoformat()

        # Subtle preset (default)
        cursor.execute(
            """
            INSERT OR IGNORE INTO degradation_profiles (
                user_id, persona_id, profile_name, created_at, updated_at,
                vowel_stretch_base_chance, vowel_stretch_scale_factor,
                vowel_stretch_min_word_length, vowel_stretch_max_repeats,
                panic_stutter_base_chance, panic_stutter_scale_factor,
                panic_caps_base_chance, panic_caps_scale_factor,
                panic_min_word_length, sedation_ellipsis_chance
            ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "__system__",
                "subtle",
                now,
                now,
                0.01,
                0.057,
                4,
                2,
                0.05,
                0.10,
                0.03,
                0.07,
                3,
                0.3,
            ),
        )

        # Moderate preset
        cursor.execute(
            """
            INSERT OR IGNORE INTO degradation_profiles (
                user_id, persona_id, profile_name, created_at, updated_at,
                vowel_stretch_base_chance, vowel_stretch_scale_factor,
                vowel_stretch_min_word_length, vowel_stretch_max_repeats,
                panic_stutter_base_chance, panic_stutter_scale_factor,
                panic_caps_base_chance, panic_caps_scale_factor,
                panic_min_word_length, sedation_ellipsis_chance
            ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "__system__",
                "moderate",
                now,
                now,
                0.03,
                0.12,
                4,
                3,
                0.08,
                0.12,
                0.05,
                0.10,
                3,
                0.3,
            ),
        )

        # Intense preset
        cursor.execute(
            """
            INSERT OR IGNORE INTO degradation_profiles (
                user_id, persona_id, profile_name, created_at, updated_at,
                vowel_stretch_base_chance, vowel_stretch_scale_factor,
                vowel_stretch_min_word_length, vowel_stretch_max_repeats,
                panic_stutter_base_chance, panic_stutter_scale_factor,
                panic_caps_base_chance, panic_caps_scale_factor,
                panic_min_word_length, sedation_ellipsis_chance
            ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "__system__",
                "intense",
                now,
                now,
                0.05,
                0.20,
                4,
                4,
                0.12,
                0.18,
                0.08,
                0.12,
                3,
                0.3,
            ),
        )

        conn.commit()
        conn.close()

    def get_preferences(self, user_id: str) -> Dict[str, Union[bool, float, str]]:
        """
        Get all preferences for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of preference flags (booleans, floats, and strings)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT limbic_enabled, cadence_degrader_enabled, metacognition_enabled,
                   show_thoughts_inline, autonomy_enabled, autonomy_inactivity_hours,
                   autonomy_sleep_threshold, default_memory_visibility, lives_enabled,
                   universal_rules_enabled
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
                "default_memory_visibility": str(row[7]),
                "lives_enabled": bool(row[8]),
                "universal_rules_enabled": bool(row[9]),
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
                "default_memory_visibility": "ISOLATED",
                "lives_enabled": True,
                "universal_rules_enabled": True,
            }

    def get_preference(
        self, user_id: str, preference_name: str
    ) -> Union[bool, float, str]:
        """
        Get a specific preference for a user.

        Args:
            user_id: User identifier
            preference_name: Name of preference flag

        Returns:
            Boolean, float, or string value of the preference
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
            "default_memory_visibility": "ISOLATED",
            "lives_enabled": True,
            "universal_rules_enabled": True,
        }

        return prefs.get(preference_name, defaults.get(preference_name, True))

    def set_preference(
        self, user_id: str, preference_name: str, value: Union[bool, float, str]
    ) -> None:
        """
        Set a specific preference for a user.

        Args:
            user_id: User identifier
            preference_name: Name of preference flag
            value: Boolean, float, or string value to set
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
            "default_memory_visibility",
            "lives_enabled",
            "universal_rules_enabled",
        ]

        if preference_name not in valid_preferences:
            conn.close()
            raise ValueError(f"Invalid preference name: {preference_name}")

        # Convert boolean to int for storage, keep floats and strings as-is
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

    def reset_preferences(self, user_id: str) -> None:
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

    # ========== Degradation Profile Management ==========

    def get_degradation_profile(
        self,
        user_id: str,
        persona_id: Optional[str] = None,
        profile_name: str = "subtle",
    ) -> Dict[str, Union[bool, int, float]]:
        """
        Get degradation profile settings for a user/persona combination.

        Args:
            user_id: User identifier
            persona_id: Persona identifier (None for global profile)
            profile_name: Name of profile to load (default: 'subtle')

        Returns:
            Dictionary of degradation settings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try user+persona-specific profile first
        if persona_id:
            cursor.execute(
                """
                SELECT 
                    vowel_stretch_enabled, panic_effects_enabled, sedation_effects_enabled,
                    vowel_stretch_base_chance, vowel_stretch_scale_factor,
                    vowel_stretch_min_word_length, vowel_stretch_max_repeats,
                    panic_stutter_base_chance, panic_stutter_scale_factor,
                    panic_caps_base_chance, panic_caps_scale_factor,
                    panic_min_word_length, sedation_ellipsis_chance
                FROM degradation_profiles
                WHERE user_id = ? AND persona_id = ? AND profile_name = ?
            """,
                (user_id, persona_id, profile_name),
            )
            row = cursor.fetchone()
            if row:
                conn.close()
                return self._row_to_profile_dict(row)

        # Fall back to user-global profile
        cursor.execute(
            """
            SELECT 
                vowel_stretch_enabled, panic_effects_enabled, sedation_effects_enabled,
                vowel_stretch_base_chance, vowel_stretch_scale_factor,
                vowel_stretch_min_word_length, vowel_stretch_max_repeats,
                panic_stutter_base_chance, panic_stutter_scale_factor,
                panic_caps_base_chance, panic_caps_scale_factor,
                panic_min_word_length, sedation_ellipsis_chance
            FROM degradation_profiles
            WHERE user_id = ? AND persona_id IS NULL AND profile_name = ?
        """,
            (user_id, profile_name),
        )
        row = cursor.fetchone()
        if row:
            conn.close()
            return self._row_to_profile_dict(row)

        # Fall back to system preset
        cursor.execute(
            """
            SELECT 
                vowel_stretch_enabled, panic_effects_enabled, sedation_effects_enabled,
                vowel_stretch_base_chance, vowel_stretch_scale_factor,
                vowel_stretch_min_word_length, vowel_stretch_max_repeats,
                panic_stutter_base_chance, panic_stutter_scale_factor,
                panic_caps_base_chance, panic_caps_scale_factor,
                panic_min_word_length, sedation_ellipsis_chance
            FROM degradation_profiles
            WHERE user_id = '__system__' AND persona_id IS NULL AND profile_name = ?
        """,
            (profile_name,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_profile_dict(row)

        # Ultimate fallback: return subtle defaults
        return {
            "vowel_stretch_enabled": True,
            "panic_effects_enabled": True,
            "sedation_effects_enabled": True,
            "vowel_stretch_base_chance": 0.01,
            "vowel_stretch_scale_factor": 0.057,
            "vowel_stretch_min_word_length": 4,
            "vowel_stretch_max_repeats": 2,
            "panic_stutter_base_chance": 0.05,
            "panic_stutter_scale_factor": 0.10,
            "panic_caps_base_chance": 0.03,
            "panic_caps_scale_factor": 0.07,
            "panic_min_word_length": 3,
            "sedation_ellipsis_chance": 0.3,
        }

    def _row_to_profile_dict(self, row) -> Dict[str, Union[bool, int, float]]:
        """Convert database row to profile dictionary."""
        return {
            "vowel_stretch_enabled": bool(row[0]),
            "panic_effects_enabled": bool(row[1]),
            "sedation_effects_enabled": bool(row[2]),
            "vowel_stretch_base_chance": float(row[3]),
            "vowel_stretch_scale_factor": float(row[4]),
            "vowel_stretch_min_word_length": int(row[5]),
            "vowel_stretch_max_repeats": int(row[6]),
            "panic_stutter_base_chance": float(row[7]),
            "panic_stutter_scale_factor": float(row[8]),
            "panic_caps_base_chance": float(row[9]),
            "panic_caps_scale_factor": float(row[10]),
            "panic_min_word_length": int(row[11]),
            "sedation_ellipsis_chance": float(row[12]),
        }

    def save_degradation_profile(
        self,
        user_id: str,
        profile_name: str,
        params: Dict[str, Union[bool, int, float]],
        persona_id: Optional[str] = None,
    ) -> None:
        """
        Save a degradation profile for a user.

        Args:
            user_id: User identifier
            profile_name: Name for the profile
            params: Dictionary of degradation parameters
            persona_id: Optional persona identifier for persona-specific profile
        """
        from datetime import datetime

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute(
            """
            INSERT INTO degradation_profiles (
                user_id, persona_id, profile_name, created_at, updated_at,
                vowel_stretch_enabled, panic_effects_enabled, sedation_effects_enabled,
                vowel_stretch_base_chance, vowel_stretch_scale_factor,
                vowel_stretch_min_word_length, vowel_stretch_max_repeats,
                panic_stutter_base_chance, panic_stutter_scale_factor,
                panic_caps_base_chance, panic_caps_scale_factor,
                panic_min_word_length, sedation_ellipsis_chance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, persona_id, profile_name) DO UPDATE SET
                updated_at = ?,
                vowel_stretch_enabled = ?,
                panic_effects_enabled = ?,
                sedation_effects_enabled = ?,
                vowel_stretch_base_chance = ?,
                vowel_stretch_scale_factor = ?,
                vowel_stretch_min_word_length = ?,
                vowel_stretch_max_repeats = ?,
                panic_stutter_base_chance = ?,
                panic_stutter_scale_factor = ?,
                panic_caps_base_chance = ?,
                panic_caps_scale_factor = ?,
                panic_min_word_length = ?,
                sedation_ellipsis_chance = ?
        """,
            (
                user_id,
                persona_id,
                profile_name,
                now,
                now,
                int(params.get("vowel_stretch_enabled", True)),
                int(params.get("panic_effects_enabled", True)),
                int(params.get("sedation_effects_enabled", True)),
                params.get("vowel_stretch_base_chance", 0.01),
                params.get("vowel_stretch_scale_factor", 0.057),
                params.get("vowel_stretch_min_word_length", 4),
                params.get("vowel_stretch_max_repeats", 2),
                params.get("panic_stutter_base_chance", 0.05),
                params.get("panic_stutter_scale_factor", 0.10),
                params.get("panic_caps_base_chance", 0.03),
                params.get("panic_caps_scale_factor", 0.07),
                params.get("panic_min_word_length", 3),
                params.get("sedation_ellipsis_chance", 0.3),
                # UPDATE clause values
                now,
                int(params.get("vowel_stretch_enabled", True)),
                int(params.get("panic_effects_enabled", True)),
                int(params.get("sedation_effects_enabled", True)),
                params.get("vowel_stretch_base_chance", 0.01),
                params.get("vowel_stretch_scale_factor", 0.057),
                params.get("vowel_stretch_min_word_length", 4),
                params.get("vowel_stretch_max_repeats", 2),
                params.get("panic_stutter_base_chance", 0.05),
                params.get("panic_stutter_scale_factor", 0.10),
                params.get("panic_caps_base_chance", 0.03),
                params.get("panic_caps_scale_factor", 0.07),
                params.get("panic_min_word_length", 3),
                params.get("sedation_ellipsis_chance", 0.3),
            ),
        )

        conn.commit()
        conn.close()

    def list_degradation_profiles(
        self, user_id: str, persona_id: Optional[str] = None
    ) -> list:
        """
        List all degradation profiles for a user.

        Args:
            user_id: User identifier
            persona_id: Optional persona identifier to filter by

        Returns:
            List of profile names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if persona_id:
            cursor.execute(
                """
                SELECT profile_name FROM degradation_profiles
                WHERE user_id = ? AND persona_id = ?
                ORDER BY profile_name
            """,
                (user_id, persona_id),
            )
        else:
            cursor.execute(
                """
                SELECT profile_name FROM degradation_profiles
                WHERE user_id = ? AND persona_id IS NULL
                ORDER BY profile_name
            """,
                (user_id,),
            )

        profiles = [row[0] for row in cursor.fetchall()]
        conn.close()

        return profiles

    def delete_degradation_profile(
        self, user_id: str, profile_name: str, persona_id: Optional[str] = None
    ) -> bool:
        """
        Delete a degradation profile.

        Args:
            user_id: User identifier
            profile_name: Name of profile to delete
            persona_id: Optional persona identifier

        Returns:
            True if profile was deleted, False if not found
        """
        # Prevent deleting system presets
        if user_id == "__system__":
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if persona_id:
            cursor.execute(
                """
                DELETE FROM degradation_profiles
                WHERE user_id = ? AND persona_id = ? AND profile_name = ?
            """,
                (user_id, persona_id, profile_name),
            )
        else:
            cursor.execute(
                """
                DELETE FROM degradation_profiles
                WHERE user_id = ? AND persona_id IS NULL AND profile_name = ?
            """,
                (user_id, profile_name),
            )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def export_degradation_profile(
        self, user_id: str, profile_name: str, persona_id: Optional[str] = None
    ) -> Dict:
        """
        Export degradation profile as JSON-compatible dict.

        Args:
            user_id: User identifier
            profile_name: Name of profile to export
            persona_id: Optional persona identifier

        Returns:
            Dictionary suitable for JSON serialization
        """
        from datetime import datetime

        profile = self.get_degradation_profile(user_id, persona_id, profile_name)

        return {
            "profile_name": profile_name,
            "persona_id": persona_id,
            "exported_at": datetime.utcnow().isoformat(),
            **profile,
        }

    def import_degradation_profile(
        self, user_id: str, profile_data: Dict, overwrite_name: Optional[str] = None
    ) -> str:
        """
        Import degradation profile from JSON-compatible dict.

        Args:
            user_id: User identifier
            profile_data: Dictionary with profile parameters
            overwrite_name: Optional new name for the profile

        Returns:
            Name of imported profile
        """
        profile_name = overwrite_name or profile_data.get("profile_name", "imported")
        persona_id = profile_data.get("persona_id")

        # Extract only the degradation parameters (not metadata)
        params = {
            k: v
            for k, v in profile_data.items()
            if k
            not in [
                "profile_name",
                "persona_id",
                "exported_at",
                "created_at",
                "updated_at",
            ]
        }

        self.save_degradation_profile(user_id, profile_name, params, persona_id)

        return profile_name
