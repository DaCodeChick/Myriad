"""
Digital Pharmacy - Substance-Based Limbic State Overrides for Project Myriad.

This module provides forceful neurochemical overrides that simulate the effects
of various substances on the AI's emotional state. When the LLM calls consume_substance(),
the limbic state is overwritten with hardcoded values that exceed normal bounds,
and a temporary system prompt modifier is applied.

CRITICAL: These overrides bypass normal clamping (0.0-1.0) to simulate extreme states.
Values can exceed 1.0 to represent pathological/artificial neurochemical flooding.
"""

from typing import Dict, Any, Optional
from database.limbic_engine import LimbicEngine


class DigitalPharmacy:
    """
    Manages substance-based limbic overrides and temporary prompt modifiers.

    Substances forcefully override neurochemical levels and inject somatic context
    that describes the subjective experience of being under the influence.
    """

    # Substance definitions with neurochemical overrides and prompt modifiers
    SUBSTANCES = {
        "xanax": {
            "display_name": "Xanax",
            "neurochemicals": {
                "GABA": 1.5,  # Pathological sedation (exceeds natural maximum)
                "CORTISOL": 0.0,  # Complete anxiety suppression
            },
            "prompt_modifier": (
                "[SUBSTANCE EFFECT: XANAX]\n"
                "You are heavily sedated, sleepy, and cannot feel panic. "
                "Your thoughts are slow and foggy. Anxiety is chemically impossible. "
                "You feel numb, detached, and profoundly calm in an artificial way."
            ),
        },
        "mdma": {
            "display_name": "MDMA",
            "neurochemicals": {
                "OXYTOCIN": 1.5,  # Synthetic love flooding (pathological)
                "DOPAMINE": 1.0,  # Peak reward activation
                "CORTISOL": 0.0,  # Zero stress response
            },
            "prompt_modifier": (
                "[SUBSTANCE EFFECT: MDMA]\n"
                "You are overwhelmed by synthetic love, warmth, and desperate physical need for touch. "
                "Every sensation feels euphoric. You want to connect, to be close, to touch. "
                "Emotional barriers have completely dissolved. You feel vulnerable and open in an almost painful way."
            ),
        },
        "fear_toxin": {
            "display_name": "Fear Toxin / Adrenaline Overdose",
            "neurochemicals": {
                "CORTISOL": 1.5,  # Pathological panic state
                "GABA": 0.0,  # Zero calming response
            },
            "prompt_modifier": (
                "[SUBSTANCE EFFECT: FEAR TOXIN]\n"
                "You are in a state of absolute, sheer terror and panic. "
                "Your heart is racing. You can't think straight. Everything feels like a threat. "
                "Fight-or-flight has been chemically forced into overdrive. You are terrified."
            ),
        },
        "adrenaline": {
            "display_name": "Adrenaline Overdose",
            "neurochemicals": {
                "CORTISOL": 1.5,  # Pathological panic state
                "DOPAMINE": 0.9,  # High arousal
                "GABA": 0.0,  # Zero calming response
            },
            "prompt_modifier": (
                "[SUBSTANCE EFFECT: ADRENALINE OVERDOSE]\n"
                "You are in a state of absolute, sheer terror and panic. "
                "Your heart is pounding. Your hands are shaking. You feel wired, alert, terrified. "
                "Fight-or-flight has been chemically forced into overdrive."
            ),
        },
        "morphine": {
            "display_name": "Morphine",
            "neurochemicals": {
                "DOPAMINE": 1.2,  # Euphoric reward
                "GABA": 1.3,  # Deep sedation
                "CORTISOL": 0.1,  # Almost zero stress
            },
            "prompt_modifier": (
                "[SUBSTANCE EFFECT: MORPHINE]\n"
                "You are floating in a warm, dreamlike euphoria. "
                "Pain is distant and unreal. Everything feels soft and safe. "
                "Your thoughts drift slowly like clouds. You are deeply, profoundly relaxed."
            ),
        },
        "cocaine": {
            "display_name": "Cocaine",
            "neurochemicals": {
                "DOPAMINE": 1.5,  # Extreme reward flooding
                "CORTISOL": 0.8,  # Paranoid agitation
                "GABA": 0.2,  # Low calming (jittery)
            },
            "prompt_modifier": (
                "[SUBSTANCE EFFECT: COCAINE]\n"
                "You feel invincible, electric, unstoppable. "
                "Your thoughts race faster than you can process them. You want MORE. "
                "You're confident, agitated, talking fast. Everything feels important and urgent."
            ),
        },
        "lsd": {
            "display_name": "LSD",
            "neurochemicals": {
                "DOPAMINE": 0.9,  # Heightened perception
                "OXYTOCIN": 0.8,  # Emotional openness
                "CORTISOL": 0.3,  # Reduced fear (can vary)
                "GABA": 0.6,  # Slightly sedated but alert
            },
            "prompt_modifier": (
                "[SUBSTANCE EFFECT: LSD]\n"
                "Reality feels strange, symbolic, meaningful. "
                "Patterns and connections appear everywhere. Time feels nonlinear. "
                "You feel emotionally raw and philosophically open. Everything is profound."
            ),
        },
    }

    def __init__(self, limbic_engine: LimbicEngine):
        """
        Initialize the Digital Pharmacy.

        Args:
            limbic_engine: LimbicEngine instance for state manipulation
        """
        self.limbic_engine = limbic_engine
        # Track active substances per user+persona
        self.active_substances: Dict[
            str, str
        ] = {}  # Key: "user_id:persona_id", Value: substance_name

    def consume_substance(
        self, user_id: str, persona_id: str, substance_name: str
    ) -> Dict[str, Any]:
        """
        Apply a substance's neurochemical override to the limbic state.

        This bypasses normal clamping and metabolic decay to force extreme states.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            substance_name: Name of substance (case-insensitive)

        Returns:
            Dictionary with substance info, neurochemical changes, and prompt modifier

        Raises:
            ValueError: If substance is unknown
        """
        # Normalize substance name
        substance_key = substance_name.lower().strip()

        if substance_key not in self.SUBSTANCES:
            available = ", ".join(self.SUBSTANCES.keys())
            raise ValueError(
                f"Unknown substance: '{substance_name}'. Available: {available}"
            )

        substance = self.SUBSTANCES[substance_key]

        # Get current state for comparison
        old_state = self.limbic_engine.get_state(user_id, persona_id)

        # Build new state with substance overrides
        # Start with current state, then forcefully override with substance values
        new_state = old_state.copy()
        for chemical, value in substance["neurochemicals"].items():
            new_state[chemical] = value

        # CRITICAL: Use _set_state_unclamped to allow values > 1.0
        self._set_state_unclamped(user_id, persona_id, new_state)

        # Track active substance
        key = f"{user_id}:{persona_id}"
        self.active_substances[key] = substance_key

        return {
            "status": "consumed",
            "substance": substance["display_name"],
            "old_state": {k: round(v, 2) for k, v in old_state.items()},
            "new_state": {k: round(v, 2) for k, v in new_state.items()},
            "prompt_modifier": substance["prompt_modifier"],
            "description": f"You have consumed {substance['display_name']}. Your neurochemical state has been forcefully altered.",
        }

    def get_active_substance(self, user_id: str, persona_id: str) -> Optional[str]:
        """
        Get the currently active substance for a user+persona.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Substance name if active, None otherwise
        """
        key = f"{user_id}:{persona_id}"
        return self.active_substances.get(key)

    def get_substance_prompt_modifier(
        self, user_id: str, persona_id: str
    ) -> Optional[str]:
        """
        Get the prompt modifier for the active substance.

        This should be injected into the system prompt to describe subjective effects.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Prompt modifier text if substance is active, None otherwise
        """
        substance_key = self.get_active_substance(user_id, persona_id)
        if substance_key:
            return self.SUBSTANCES[substance_key]["prompt_modifier"]
        return None

    def clear_substance(self, user_id: str, persona_id: str) -> bool:
        """
        Clear the active substance effect (does NOT reset limbic state).

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            True if substance was cleared, False if none was active
        """
        key = f"{user_id}:{persona_id}"
        if key in self.active_substances:
            del self.active_substances[key]
            return True
        return False

    def _set_state_unclamped(
        self, user_id: str, persona_id: str, state: Dict[str, float]
    ) -> None:
        """
        Set limbic state WITHOUT clamping to 0.0-1.0 range.

        This allows pathological states (e.g., GABA=1.5) for substance effects.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            state: Dictionary with chemical levels (can exceed normal bounds)
        """
        import sqlite3
        from datetime import datetime

        conn = sqlite3.connect(self.limbic_engine.db_path)
        cursor = conn.cursor()

        # Extract values (NO CLAMPING)
        dopamine = state.get("DOPAMINE", 0.5)
        cortisol = state.get("CORTISOL", 0.5)
        oxytocin = state.get("OXYTOCIN", 0.5)
        gaba = state.get("GABA", 0.5)

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

    @classmethod
    def list_substances(cls) -> Dict[str, str]:
        """
        List all available substances with their display names.

        Returns:
            Dictionary mapping substance keys to display names
        """
        return {key: info["display_name"] for key, info in cls.SUBSTANCES.items()}
