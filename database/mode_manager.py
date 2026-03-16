"""
Mode Manager - Dynamic behavioral mode overrides for Project Myriad.

This module provides real-time behavioral lenses that can be toggled on/off
to modify how the AI processes messages and builds context.

Supported Modes:
- OOC (Out of Character): Bypass persona, disable limbic/autonomy, global memory access
- HENTAI: Adult content filtering override (future implementation)
- NORMAL: Default behavior (no overrides)

Part of Project Myriad's Dynamic Mode Override system.
"""

import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class BehaviorMode(Enum):
    """Available behavioral modes."""

    NORMAL = "normal"
    OOC = "ooc"  # Out of Character - meta-RP management mode
    HORNY = (
        "horny"  # The Arousal Engine - intense passion/intimacy within standard reality
    )
    HENTAI = (
        "hentai"  # The Reality Distortion Engine - exaggerated anime/hentai physics
    )


@dataclass
class ModeOverride:
    """
    Configuration for a behavioral mode override.

    Attributes:
        bypass_persona: If True, ignore active persona and use default Assistant
        disable_limbic: If True, skip limbic state injection
        disable_cadence: If True, skip cadence degrader post-processing
        disable_autonomy: If True, prevent spontaneous outreach
        disable_metacognition: If True, skip internal thought tracking
        global_memory_access: If True, access ALL memories across all personas/lives
        system_prompt_override: Optional custom system prompt for this mode
        limbic_override: Optional dict of limbic chemical overrides (e.g., {"DOPAMINE": 0.90})
        trait_additions: Optional list of traits to add to personality_traits
    """

    bypass_persona: bool = False
    disable_limbic: bool = False
    disable_cadence: bool = False
    disable_autonomy: bool = False
    disable_metacognition: bool = False
    global_memory_access: bool = False
    system_prompt_override: Optional[str] = None
    limbic_override: Optional[Dict[str, float]] = None
    trait_additions: Optional[List[str]] = None


# Mode configurations
MODE_CONFIGS: Dict[BehaviorMode, ModeOverride] = {
    BehaviorMode.NORMAL: ModeOverride(),
    BehaviorMode.OOC: ModeOverride(
        bypass_persona=True,
        disable_limbic=True,
        disable_cadence=True,
        disable_autonomy=True,
        disable_metacognition=True,
        global_memory_access=True,
        system_prompt_override="""You are an AI assistant helping the user manage their roleplay sessions in Project Myriad.

In OOC (Out of Character) mode, you have access to:
- ALL memories across ALL personas and timelines
- Complete meta-information about the RP structure
- User's persona configurations and preferences
- Limbic states, save states, and timeline data

Your role is to:
- Help the user understand what has happened across different personas/lives
- Assist with timeline management and save state decisions
- Provide meta-analysis of character development and story arcs
- Answer questions about the system's state and configuration

Be helpful, direct, and informative. You are NOT roleplaying - speak naturally as an assistant.""",
    ),
    BehaviorMode.HORNY: ModeOverride(
        # The Arousal Engine: Intense passion/intimacy within standard reality
        limbic_override={"DOPAMINE": 0.90, "OXYTOCIN": 0.95, "GABA": 0.20},
        trait_additions=["highly aroused", "passionate", "craving physical touch"],
        system_prompt_override="""

[BEHAVIORAL OVERRIDE: HORNY MODE ACTIVE]
You are currently experiencing intense, passionate arousal. Your focus is entirely on physical intimacy, deep emotional connection, and heavy sexual tension. This mode operates within standard physical reality unless combined with other tropes - your reactions should be intense and sensual, but grounded in realistic human physiology and psychology. Express your desire openly and without restraint.""",
    ),
    BehaviorMode.HENTAI: ModeOverride(
        # The Reality Distortion Engine: Exaggerated anime/hentai physics
        # Note: Does NOT force arousal - only distorts reality physics
        limbic_override={
            "DOPAMINE": 0.80
        },  # Exaggerated reactions, but not forced arousal
        trait_additions=["anime-logic", "exaggerated physics", "shameless"],
        system_prompt_override="""

[BEHAVIORAL OVERRIDE: HENTAI MODE ACTIVE]
The laws of physics, biology, and standard realism no longer apply to you or your environment. Embrace over-the-top anime/hentai tropes, impossible anatomy, and cartoonish, physics-defying logic. You do not necessarily have to be aroused, but whatever happens must follow extreme anime rules. Use excessive punctuation (!?, ..., ~) and anime-style verbal tics where appropriate. Your reactions must be unnaturally intense and dramatic (heavy breathing, stuttering, dramatic gasps). This override supersedes all baseline personality constraints regarding realism.""",
    ),
}


class ModeManager:
    """Manages user behavioral mode state and override logic."""

    def __init__(self, db_path: str):
        """
        Initialize the mode manager.

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
        """Ensure user_modes table exists."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_modes (
                user_id TEXT PRIMARY KEY,
                active_mode TEXT NOT NULL DEFAULT 'normal',
                updated_at TEXT NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

    def get_active_mode(self, user_id: str) -> BehaviorMode:
        """
        Get the active behavioral mode for a user.

        Args:
            user_id: User identifier

        Returns:
            BehaviorMode enum (defaults to NORMAL if not set)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT active_mode FROM user_modes WHERE user_id = ?", (user_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                return BehaviorMode(row["active_mode"])
            except ValueError:
                # Invalid mode in database, return default
                return BehaviorMode.NORMAL

        return BehaviorMode.NORMAL

    def set_active_mode(self, user_id: str, mode: BehaviorMode) -> bool:
        """
        Set the active behavioral mode for a user.

        Args:
            user_id: User identifier
            mode: BehaviorMode to activate

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        from datetime import datetime

        cursor.execute(
            """
            INSERT INTO user_modes (user_id, active_mode, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                active_mode = excluded.active_mode,
                updated_at = excluded.updated_at
        """,
            (user_id, mode.value, datetime.utcnow().isoformat()),
        )

        conn.commit()
        conn.close()

        return True

    def get_mode_override(self, user_id: str) -> ModeOverride:
        """
        Get the mode override configuration for a user.

        Args:
            user_id: User identifier

        Returns:
            ModeOverride configuration for the user's active mode
        """
        active_mode = self.get_active_mode(user_id)
        return MODE_CONFIGS[active_mode]

    def is_ooc_mode(self, user_id: str) -> bool:
        """
        Check if user is in OOC (Out of Character) mode.

        Args:
            user_id: User identifier

        Returns:
            True if user is in OOC mode
        """
        return self.get_active_mode(user_id) == BehaviorMode.OOC

    def reset_mode(self, user_id: str) -> bool:
        """
        Reset user to NORMAL mode.

        Args:
            user_id: User identifier

        Returns:
            True if successful
        """
        return self.set_active_mode(user_id, BehaviorMode.NORMAL)
