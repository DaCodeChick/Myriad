"""
Persona data models and validation.

Defines the PersonaCartridge and PersonaRelationship dataclasses that represent
loaded persona configurations.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class PersonaRelationship:
    """
    Represents a relationship override for a specific target.

    Special target_id values:
    - "@user": Applies when the user is NOT wearing a mask (unmasked/anonymous users)
    - Any other string: Matches against the persona_id of the user's active mask

    This allows personas to define different behaviors for:
    1. Unmasked users (target_id: "@user")
    2. Specific persona masks (target_id: "user_masks/schala", etc.)
    """

    target_id: str
    description: str
    personality_traits_override: Optional[List[str]] = None
    rules_of_engagement_override: Optional[List[str]] = None
    limbic_baseline_override: Optional[Dict[str, float]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaRelationship":
        """Create a PersonaRelationship from a dictionary."""
        return cls(
            target_id=data["target_id"],
            description=data["description"],
            personality_traits_override=data.get("personality_traits_override"),
            rules_of_engagement_override=data.get("rules_of_engagement_override"),
            limbic_baseline_override=data.get("limbic_baseline_override"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary format."""
        result = {
            "target_id": self.target_id,
            "description": self.description,
        }
        if self.personality_traits_override:
            result["personality_traits_override"] = self.personality_traits_override
        if self.rules_of_engagement_override:
            result["rules_of_engagement_override"] = self.rules_of_engagement_override
        if self.limbic_baseline_override:
            result["limbic_baseline_override"] = self.limbic_baseline_override
        return result


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
    limbic_baseline: Optional[Dict[str, float]] = None
    relationships: Optional[List[PersonaRelationship]] = None
    appearance: Optional[str] = None  # Manual fallback appearance from metadata.json
    cached_appearance: Optional[str] = None  # Vision-generated, loaded from database
    is_narrator: bool = False  # Dungeon Master/Narrator personas (no physical body)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaCartridge":
        """Create a PersonaCartridge from a dictionary (loaded JSON)."""
        # Parse relationships if present
        relationships = None
        if "relationships" in data and data["relationships"]:
            relationships = [
                PersonaRelationship.from_dict(rel) for rel in data["relationships"]
            ]

        return cls(
            persona_id=data["persona_id"],
            name=data["name"],
            system_prompt=data["system_prompt"],
            personality_traits=data.get("personality_traits", []),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1000),
            rules_of_engagement=data.get("rules_of_engagement"),
            background=data.get("background"),
            appearance=data.get("appearance"),
            cached_appearance=data.get("cached_appearance"),
            limbic_baseline=data.get("limbic_baseline"),
            relationships=relationships,
            is_narrator=data.get("is_narrator", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert persona to dictionary format (for metadata.json)."""
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
        if self.appearance:
            result["appearance"] = self.appearance
        # Note: cached_appearance is NOT included (stored in database only)
        if self.limbic_baseline:
            result["limbic_baseline"] = self.limbic_baseline
        if self.relationships:
            result["relationships"] = [rel.to_dict() for rel in self.relationships]
        if self.is_narrator:
            result["is_narrator"] = self.is_narrator
        return result

    def get_relationship_override(
        self, target_id: str
    ) -> Optional[PersonaRelationship]:
        """
        Find a relationship override for a specific target.

        Args:
            target_id: The ID to match (user mask ID or another persona ID)

        Returns:
            PersonaRelationship if found, None otherwise
        """
        if not self.relationships:
            return None

        for relationship in self.relationships:
            if relationship.target_id == target_id:
                return relationship

        return None
