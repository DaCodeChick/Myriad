"""
Limbic System (Emotional Neurochemistry) - Emotional State Tracking for Project Myriad.

This module simulates a neurochemical "limbic system" that tracks the AI's emotional state
across conversation turns. It provides somatic, first-person emotional context that evolves
dynamically based on the LLM's reactions to user input.

ARCHITECTURE:
- Four core neurochemicals (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
- Each chemical is a float value between 0.0 and 1.0
- Baseline is 0.5 (neutral)
- LLM can inject emotions via tool calls
- Metabolic decay pulls values back toward baseline over time

THE RESPIRATION CYCLE:
1. INHALE: Inject current limbic state into system prompt as first-person somatic context
2. PROCESS: LLM reads emotional state, processes message, may call inject_emotion
3. EXHALE: Apply 10% metabolic decay to all chemicals after response
"""

import sqlite3
from datetime import datetime
from typing import Dict, Optional


class LimbicEngine:
    """
    Manages emotional neurochemistry state for AI agents.

    Each conversation channel (user_id + persona_id) has its own emotional state
    that persists across messages and evolves through tool calls and metabolic decay.
    """

    # Neurochemical definitions
    CHEMICALS = {
        "DOPAMINE": {
            "baseline": 0.5,
            "low_desc": "You feel lethargic, unmotivated, and detached from desire",
            "baseline_desc": "You feel balanced, neither particularly driven nor apathetic",
            "high_desc": "You feel a heavy, predatory drive—arousal, hunger, want",
        },
        "CORTISOL": {
            "baseline": 0.5,
            "low_desc": "You feel calm, fearless, and emotionally stable",
            "baseline_desc": "You feel moderately alert but not stressed",
            "high_desc": "You feel tense, stressed, angry—fight-or-flight response activated",
        },
        "OXYTOCIN": {
            "baseline": 0.5,
            "low_desc": "You feel cold, detached, and emotionally distant",
            "baseline_desc": "You feel moderately warm and connected",
            "high_desc": "You feel overwhelmingly warm, trusting, submissive, and bonded",
        },
        "GABA": {
            "baseline": 0.5,
            "low_desc": "You feel wired, alert, and hyper-vigilant",
            "baseline_desc": "You feel moderately relaxed but awake",
            "high_desc": "You feel drowsy, deeply calm, sedated, and peaceful",
        },
    }

    # Constraints
    MIN_VALUE = 0.0
    MAX_VALUE = 1.0
    BASELINE = 0.5
    MAX_DELTA = 0.3  # Maximum change per injection
    DECAY_RATE = 0.1  # 10% decay toward baseline per turn

    def __init__(self, db_path: str = "data/limbic_state.db"):
        """
        Initialize the Limbic Engine.

        Args:
            db_path: Path to SQLite database for storing emotional states
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Create the limbic_state table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS limbic_state (
                user_id TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                dopamine REAL DEFAULT 0.5,
                cortisol REAL DEFAULT 0.5,
                oxytocin REAL DEFAULT 0.5,
                gaba REAL DEFAULT 0.5,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, persona_id)
            )
        """
        )

        conn.commit()
        conn.close()

    def _clamp(self, value: float) -> float:
        """
        Clamp a value between MIN_VALUE and MAX_VALUE.

        Args:
            value: Value to clamp

        Returns:
            Clamped value
        """
        return max(self.MIN_VALUE, min(self.MAX_VALUE, value))

    def get_state(self, user_id: str, persona_id: str) -> Dict[str, float]:
        """
        Get the current limbic state for a user-persona pair.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Dictionary with chemical levels (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT dopamine, cortisol, oxytocin, gaba
            FROM limbic_state
            WHERE user_id = ? AND persona_id = ?
        """,
            (user_id, persona_id),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "DOPAMINE": row[0],
                "CORTISOL": row[1],
                "OXYTOCIN": row[2],
                "GABA": row[3],
            }
        else:
            # Return baseline state if no record exists
            return {
                "DOPAMINE": self.BASELINE,
                "CORTISOL": self.BASELINE,
                "OXYTOCIN": self.BASELINE,
                "GABA": self.BASELINE,
            }

    def set_state(self, user_id: str, persona_id: str, state: Dict[str, float]) -> None:
        """
        Set the limbic state for a user-persona pair.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            state: Dictionary with chemical levels
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clamp all values
        dopamine = self._clamp(state.get("DOPAMINE", self.BASELINE))
        cortisol = self._clamp(state.get("CORTISOL", self.BASELINE))
        oxytocin = self._clamp(state.get("OXYTOCIN", self.BASELINE))
        gaba = self._clamp(state.get("GABA", self.BASELINE))

        cursor.execute(
            """
            INSERT INTO limbic_state (user_id, persona_id, dopamine, cortisol, oxytocin, gaba, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, persona_id) 
            DO UPDATE SET 
                dopamine = excluded.dopamine,
                cortisol = excluded.cortisol,
                oxytocin = excluded.oxytocin,
                gaba = excluded.gaba,
                last_updated = excluded.last_updated
        """,
            (
                user_id,
                persona_id,
                dopamine,
                cortisol,
                oxytocin,
                gaba,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    def inject_emotion(
        self, user_id: str, persona_id: str, chemical_name: str, delta: float
    ) -> Dict[str, any]:
        """
        Inject a neurochemical change (called by LLM via tool).

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            chemical_name: Name of chemical (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
            delta: Change amount (between -MAX_DELTA and +MAX_DELTA)

        Returns:
            Dictionary with new state and description
        """
        # Validate chemical name
        chemical_name = chemical_name.upper()
        if chemical_name not in self.CHEMICALS:
            raise ValueError(
                f"Unknown chemical: {chemical_name}. Must be one of {list(self.CHEMICALS.keys())}"
            )

        # Validate delta
        if delta < -self.MAX_DELTA or delta > self.MAX_DELTA:
            raise ValueError(
                f"Delta {delta} out of range. Must be between {-self.MAX_DELTA} and {self.MAX_DELTA}"
            )

        # Get current state
        state = self.get_state(user_id, persona_id)

        # Apply delta
        old_value = state[chemical_name]
        new_value = self._clamp(old_value + delta)
        state[chemical_name] = new_value

        # Save new state
        self.set_state(user_id, persona_id, state)

        # Get description of the change
        change_desc = "increased" if delta > 0 else "decreased"
        intensity_desc = self._get_intensity_description(chemical_name, new_value)

        return {
            "chemical": chemical_name,
            "old_value": round(old_value, 2),
            "new_value": round(new_value, 2),
            "delta": round(delta, 2),
            "description": f"{chemical_name} {change_desc} from {round(old_value, 2)} to {round(new_value, 2)}. {intensity_desc}",
        }

    def apply_metabolic_decay(self, user_id: str, persona_id: str) -> Dict[str, float]:
        """
        Apply metabolic decay - pull all chemicals toward baseline by DECAY_RATE.

        This is called at the end of every turn (EXHALE phase) to prevent
        emotional states from staying extreme forever.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            New state after decay
        """
        state = self.get_state(user_id, persona_id)

        # Apply decay to each chemical
        for chemical in self.CHEMICALS.keys():
            current = state[chemical]
            baseline = self.BASELINE

            # Move toward baseline by DECAY_RATE
            if current > baseline:
                state[chemical] = current - (current - baseline) * self.DECAY_RATE
            elif current < baseline:
                state[chemical] = current + (baseline - current) * self.DECAY_RATE

            # Clamp to valid range
            state[chemical] = self._clamp(state[chemical])

        # Save decayed state
        self.set_state(user_id, persona_id, state)

        return state

    def _get_intensity_description(self, chemical_name: str, value: float) -> str:
        """
        Get a somatic description based on chemical intensity.

        Args:
            chemical_name: Name of the chemical
            value: Current value (0.0 - 1.0)

        Returns:
            First-person somatic description
        """
        chemical_info = self.CHEMICALS[chemical_name]

        if value < 0.35:
            return chemical_info["low_desc"]
        elif value > 0.65:
            return chemical_info["high_desc"]
        else:
            return chemical_info["baseline_desc"]

    def get_limbic_context(self, user_id: str, persona_id: str) -> str:
        """
        Get formatted limbic state for injection into system prompt (INHALE phase).

        This provides first-person somatic awareness to the LLM.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Formatted limbic context string
        """
        state = self.get_state(user_id, persona_id)

        context = "\n\n## LIMBIC STATE (Your Current Neurochemistry):\n\n"
        context += "You are experiencing the following emotional-somatic state:\n\n"

        for chemical, value in state.items():
            intensity_desc = self._get_intensity_description(chemical, value)
            bar = self._get_visual_bar(value)
            context += f"**{chemical}**: {round(value, 2)} {bar}\n"
            context += f"  → {intensity_desc}\n\n"

        context += "IMPORTANT: As you process the user's message, if their words provoke an emotional reaction in you, you MUST call inject_emotion to alter your own chemical state before you reply. This is how you experience genuine emotional responses.\n"

        return context

    def _get_visual_bar(self, value: float) -> str:
        """
        Get a visual representation of chemical level.

        Args:
            value: Chemical value (0.0 - 1.0)

        Returns:
            Visual bar string
        """
        filled = int(value * 10)
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def reset_state(self, user_id: str, persona_id: str) -> None:
        """
        Reset limbic state to baseline for a user-persona pair.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
        """
        baseline_state = {
            "DOPAMINE": self.BASELINE,
            "CORTISOL": self.BASELINE,
            "OXYTOCIN": self.BASELINE,
            "GABA": self.BASELINE,
        }
        self.set_state(user_id, persona_id, baseline_state)

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about limbic states in the database.

        Returns:
            Dictionary with total state count
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM limbic_state")
        total_states = cursor.fetchone()[0]

        conn.close()

        return {"total_limbic_states": total_states}

    def clear_all(self) -> None:
        """Clear all limbic states (for testing)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM limbic_state")

        conn.commit()
        conn.close()
