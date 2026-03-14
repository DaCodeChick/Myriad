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

    def clear_cache(self):
        """Clear all cached personas (forces reload on next access)."""
        self._cache.clear()
