"""
Digital Pharmacy - Substance-Based Limbic State Overrides for Project Myriad.

This module provides forceful neurochemical overrides that simulate the effects
of various substances on the AI's emotional state. When the LLM calls consume_substance(),
the limbic state is overwritten with values loaded from JSON cartridges that exceed normal bounds,
and a temporary system prompt modifier is applied.

CRITICAL: These overrides bypass normal clamping (0.0-1.0) to simulate extreme states.
Values can exceed 1.0 to represent pathological/artificial neurochemical flooding.

ARCHITECTURE: Follows the same hot-swappable cartridge pattern as PersonaLoader.
Substances are stored as individual .json files in the pharmacy/ directory.
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from database.limbic_engine import LimbicEngine


@dataclass
class SubstanceCartridge:
    """Represents a loaded substance cartridge with all its configuration."""

    substance_id: str
    display_name: str
    neurochemicals: Dict[str, float]
    prompt_modifier: str
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubstanceCartridge":
        """Create a SubstanceCartridge from a dictionary (loaded JSON)."""
        return cls(
            substance_id=data["substance_id"],
            display_name=data["display_name"],
            neurochemicals=data["neurochemicals"],
            prompt_modifier=data["prompt_modifier"],
            description=data.get("description"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert substance to dictionary format."""
        result = {
            "substance_id": self.substance_id,
            "display_name": self.display_name,
            "neurochemicals": self.neurochemicals,
            "prompt_modifier": self.prompt_modifier,
        }
        if self.description:
            result["description"] = self.description
        return result


class DigitalPharmacy:
    """
    Manages substance-based limbic overrides and temporary prompt modifiers.

    Substances are loaded dynamically from JSON files in the pharmacy/ directory,
    following the same hot-swappable cartridge pattern as PersonaLoader.
    """

    def __init__(self, limbic_engine: LimbicEngine, pharmacy_dir: str = "pharmacy"):
        """
        Initialize the Digital Pharmacy.

        Args:
            limbic_engine: LimbicEngine instance for state manipulation
            pharmacy_dir: Directory containing substance JSON files (default: pharmacy/)
        """
        self.limbic_engine = limbic_engine
        self.pharmacy_dir = pharmacy_dir
        self._cache: Dict[str, SubstanceCartridge] = {}

        # Track active substances per user+persona
        self.active_substances: Dict[
            str, str
        ] = {}  # Key: "user_id:persona_id", Value: substance_id

        # Ensure pharmacy directory exists
        os.makedirs(pharmacy_dir, exist_ok=True)

        # Load all substances on initialization
        self._load_all_substances()

    def _load_all_substances(self) -> None:
        """
        Scan the pharmacy directory and load all substance JSON files into cache.

        This is called on initialization to populate the available substances.
        """
        if not os.path.exists(self.pharmacy_dir):
            print(
                f"[Digital Pharmacy] Warning: pharmacy directory '{self.pharmacy_dir}' does not exist"
            )
            return

        for filename in os.listdir(self.pharmacy_dir):
            if filename.endswith(".json"):
                substance_id = filename[:-5]  # Remove .json extension
                substance = self.load_substance(substance_id)
                if substance:
                    print(
                        f"[Digital Pharmacy] Loaded substance: {substance.display_name} ({substance_id})"
                    )

    def load_substance(self, substance_id: str) -> Optional[SubstanceCartridge]:
        """
        Load a substance cartridge from disk.

        Args:
            substance_id: The ID of the substance to load (filename without .json)

        Returns:
            SubstanceCartridge if found and valid, None otherwise
        """
        # Check cache first
        if substance_id in self._cache:
            return self._cache[substance_id]

        # Load from disk
        file_path = os.path.join(self.pharmacy_dir, f"{substance_id}.json")

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate required fields
            required_fields = [
                "substance_id",
                "display_name",
                "neurochemicals",
                "prompt_modifier",
            ]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Ensure substance_id in file matches filename
            if data["substance_id"] != substance_id:
                raise ValueError(
                    f"substance_id '{data['substance_id']}' does not match "
                    f"filename '{substance_id}.json'"
                )

            # Create substance cartridge
            substance = SubstanceCartridge.from_dict(data)

            # Cache it
            self._cache[substance_id] = substance

            return substance

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"[Digital Pharmacy] Error loading substance '{substance_id}': {e}")
            return None

    def get_substance(self, substance_id: str) -> Optional[SubstanceCartridge]:
        """
        Get a substance cartridge (alias for load_substance for cleaner API).

        Args:
            substance_id: The ID of the substance to get

        Returns:
            SubstanceCartridge if found, None otherwise
        """
        return self.load_substance(substance_id)

    def list_available_substances(self) -> List[str]:
        """
        List all available substance IDs in the pharmacy directory.

        Returns:
            List of substance_id strings (filenames without .json extension)
        """
        if not os.path.exists(self.pharmacy_dir):
            return []

        substances = []
        for filename in os.listdir(self.pharmacy_dir):
            if filename.endswith(".json"):
                substance_id = filename[:-5]  # Remove .json extension
                substances.append(substance_id)

        return sorted(substances)

    def reload_substance(self, substance_id: str) -> Optional[SubstanceCartridge]:
        """
        Force reload a substance from disk, bypassing cache.

        Args:
            substance_id: The ID of the substance to reload

        Returns:
            SubstanceCartridge if found and valid, None otherwise
        """
        # Clear from cache
        if substance_id in self._cache:
            del self._cache[substance_id]

        # Load fresh from disk
        return self.load_substance(substance_id)

    def consume_substance(
        self, user_id: str, persona_id: str, substance_name: str
    ) -> str:
        """
        Apply a substance's neurochemical override to the limbic state.

        This bypasses normal clamping and metabolic decay to force extreme states.

        Args:
            user_id: User identifier
            persona_id: Persona identifier
            substance_name: Name of substance (substance_id, case-insensitive)

        Returns:
            Human-readable response string describing the consumption

        Raises:
            ValueError: If substance is unknown
        """
        # Normalize substance name
        substance_id = substance_name.lower().strip()

        # Load substance (will use cache if already loaded)
        substance = self.load_substance(substance_id)

        if not substance:
            available = ", ".join(self.list_available_substances())
            return f"Error: Unknown substance '{substance_name}'. Available substances: {available}"

        # Get current state for comparison
        old_state = self.limbic_engine.get_state(user_id, persona_id)

        # Build new state with substance overrides
        # Start with current state, then forcefully override with substance values
        new_state = old_state.copy()
        for chemical, value in substance.neurochemicals.items():
            new_state[chemical] = value

        # CRITICAL: Use _set_state_unclamped to allow values > 1.0
        self._set_state_unclamped(user_id, persona_id, new_state)

        # Track active substance
        key = f"{user_id}:{persona_id}"
        self.active_substances[key] = substance_id

        # Build response message
        old_state_str = ", ".join([f"{k}={v:.2f}" for k, v in old_state.items()])
        new_state_str = ", ".join([f"{k}={v:.2f}" for k, v in new_state.items()])

        return (
            f"You have consumed {substance.display_name}.\n\n"
            f"Previous neurochemical state: {old_state_str}\n"
            f"Current neurochemical state: {new_state_str}\n\n"
            f"The substance is now active and will influence your emotional state."
        )

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
        substance_id = self.get_active_substance(user_id, persona_id)
        if substance_id:
            substance = self.load_substance(substance_id)
            if substance:
                return substance.prompt_modifier
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

    def get_substance_info(self, substance_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a substance.

        Args:
            substance_id: The substance ID to query

        Returns:
            Dictionary with substance info, or None if not found
        """
        substance = self.load_substance(substance_id)
        if substance:
            return {
                "substance_id": substance.substance_id,
                "display_name": substance.display_name,
                "neurochemicals": substance.neurochemicals,
                "description": substance.description,
            }
        return None
