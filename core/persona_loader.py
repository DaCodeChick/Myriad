"""
Persona Cartridge System - Hot-swappable personality loader for Project Myriad.

This module handles loading and validating persona.json files from the personas/
directory and its subdirectories (supporting categorization).
"""

import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PersonaCartridge:
    """Represents a loaded persona cartridge with all its configuration."""

    persona_id: str
    name: str
    system_prompt: str
    personality_traits: List[str]
    temperature: float
    max_tokens: int
    rules_of_engagement: Optional[List[str]] = None
    background: Optional[str] = None
    cached_appearance: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaCartridge":
        """Create a PersonaCartridge from a dictionary (loaded JSON)."""
        return cls(
            persona_id=data["persona_id"],
            name=data["name"],
            system_prompt=data["system_prompt"],
            personality_traits=data.get("personality_traits", []),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1000),
            rules_of_engagement=data.get("rules_of_engagement"),
            background=data.get("background"),
            cached_appearance=data.get("cached_appearance"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert persona to dictionary format."""
        result = {
            "persona_id": self.persona_id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "personality_traits": self.personality_traits,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.rules_of_engagement:
            result["rules_of_engagement"] = self.rules_of_engagement
        if self.background:
            result["background"] = self.background
        if self.cached_appearance:
            result["cached_appearance"] = self.cached_appearance
        return result


class PersonaLoader:
    """Manages loading and caching of persona cartridges."""

    def __init__(self, personas_dir: str = "personas"):
        """
        Initialize the persona loader.

        Args:
            personas_dir: Directory containing persona.json files
        """
        self.personas_dir = personas_dir
        self._cache: Dict[str, PersonaCartridge] = {}

        # Ensure personas directory exists
        os.makedirs(personas_dir, exist_ok=True)

    def load_persona(self, persona_id: str) -> Optional[PersonaCartridge]:
        """
        Load a persona cartridge from disk.

        Supports both flat and categorized personas:
        - "coding_mentor" -> personas/coding_mentor.json (legacy)
        - "professional/coding_mentor" -> personas/professional/coding_mentor.json

        Args:
            persona_id: The ID of the persona to load (can include category path)

        Returns:
            PersonaCartridge if found and valid, None otherwise
        """
        # Check cache first
        if persona_id in self._cache:
            return self._cache[persona_id]

        # Build file path (persona_id can include subdirectories)
        file_path = os.path.join(self.personas_dir, f"{persona_id}.json")

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ["persona_id", "name", "system_prompt"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Ensure persona_id in file matches the requested ID
            if data["persona_id"] != persona_id:
                raise ValueError(
                    f"persona_id '{data['persona_id']}' does not match "
                    f"requested ID '{persona_id}'"
                )

            # Create persona cartridge
            persona = PersonaCartridge.from_dict(data)

            # Cache it
            self._cache[persona_id] = persona

            return persona

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Error loading persona '{persona_id}': {e}")
            return None

    def get_persona(self, persona_id: str) -> Optional[PersonaCartridge]:
        """
        Get a persona cartridge (alias for load_persona for cleaner API).

        Args:
            persona_id: The ID of the persona to get

        Returns:
            PersonaCartridge if found, None otherwise
        """
        return self.load_persona(persona_id)

    def list_available_personas(self) -> List[str]:
        """
        List all available persona IDs in the personas directory (recursively).

        Returns categorized personas with their full path:
        - "professional/coding_mentor"
        - "nsfw/romantic/alpha_stud"

        Returns:
            List of persona_id strings sorted alphabetically
        """
        if not os.path.exists(self.personas_dir):
            return []

        personas = []
        personas_path = Path(self.personas_dir)

        # Recursively find all .json files
        for json_file in personas_path.rglob("*.json"):
            # Get relative path from personas directory
            relative_path = json_file.relative_to(personas_path)
            # Remove .json extension and convert to forward slashes
            persona_id = str(relative_path.with_suffix("")).replace(os.sep, "/")
            personas.append(persona_id)

        return sorted(personas)

    def reload_persona(self, persona_id: str) -> Optional[PersonaCartridge]:
        """
        Force reload a persona from disk, bypassing cache.

        Args:
            persona_id: The ID of the persona to reload

        Returns:
            PersonaCartridge if found and valid, None otherwise
        """
        # Clear from cache
        if persona_id in self._cache:
            del self._cache[persona_id]

        # Load fresh from disk
        return self.load_persona(persona_id)

    def clear_cache(self) -> None:
        """Clear all cached personas (forces reload on next access)."""
        self._cache.clear()

    def update_persona_background(
        self, persona_id: str, background: Optional[str]
    ) -> bool:
        """
        Update the background field of an existing persona and save to disk.

        Args:
            persona_id: The ID of the persona to update
            background: The new background text to set, or None to clear it

        Returns:
            True if successful, False if persona doesn't exist or update failed
        """
        # Load the persona first to ensure it exists
        persona = self.load_persona(persona_id)
        if not persona:
            return False

        # Update the background field
        persona.background = background

        # Build file path
        file_path = os.path.join(self.personas_dir, f"{persona_id}.json")

        try:
            # Convert to dict and write to file with pretty formatting
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(persona.to_dict(), f, indent=2, ensure_ascii=False)

            # Update cache
            self._cache[persona_id] = persona

            return True

        except (OSError, ValueError) as e:
            print(f"Error updating persona '{persona_id}': {e}")
            return False

    def update_persona_appearance(
        self, persona_id: str, cached_appearance: Optional[str]
    ) -> bool:
        """
        Update the cached_appearance field of an existing persona and save to disk.

        Args:
            persona_id: The ID of the persona to update
            cached_appearance: The new appearance description, or None to clear it

        Returns:
            True if successful, False if persona doesn't exist or update failed
        """
        # Load the persona first to ensure it exists
        persona = self.load_persona(persona_id)
        if not persona:
            return False

        # Update the cached_appearance field
        persona.cached_appearance = cached_appearance

        # Build file path
        file_path = os.path.join(self.personas_dir, f"{persona_id}.json")

        try:
            # Convert to dict and write to file with pretty formatting
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(persona.to_dict(), f, indent=2, ensure_ascii=False)

            # Update cache
            self._cache[persona_id] = persona

            return True

        except (OSError, ValueError) as e:
            print(f"Error updating persona appearance '{persona_id}': {e}")
            return False

    def create_persona(
        self,
        persona_id: str,
        name: str,
        system_prompt: str,
        personality_traits: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        rules_of_engagement: Optional[List[str]] = None,
        background: Optional[str] = None,
    ) -> bool:
        """
        Create a new persona and save to disk.

        Args:
            persona_id: Unique ID for the persona (can include category path)
            name: Display name for the persona
            system_prompt: Core identity and behavioral prompt
            personality_traits: List of personality trait keywords
            temperature: LLM temperature setting (0.0-2.0)
            max_tokens: Maximum tokens for responses
            rules_of_engagement: Persona-specific behavioral rules
            background: Optional background/lore text for deep context

        Returns:
            True if successful, False if persona already exists or creation failed
        """
        # Check if persona already exists
        file_path = os.path.join(self.personas_dir, f"{persona_id}.json")
        if os.path.exists(file_path):
            print(f"Persona '{persona_id}' already exists")
            return False

        # Create persona cartridge
        persona = PersonaCartridge(
            persona_id=persona_id,
            name=name,
            system_prompt=system_prompt,
            personality_traits=personality_traits or [],
            temperature=temperature,
            max_tokens=max_tokens,
            rules_of_engagement=rules_of_engagement,
            background=background,
        )

        try:
            # Ensure directory exists for categorized personas
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write to file with pretty formatting
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(persona.to_dict(), f, indent=2, ensure_ascii=False)

            # Cache it
            self._cache[persona_id] = persona

            return True

        except (OSError, ValueError) as e:
            print(f"Error creating persona '{persona_id}': {e}")
            return False
