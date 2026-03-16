"""
Scenario data model.

Defines the Scenario dataclass representing hierarchical environmental contexts.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Scenario:
    """Represents a scenario/location in the world tree."""

    name: str
    description: str
    parent_name: Optional[str] = None
    appearance: Optional[str] = None  # Manual fallback appearance from JSON
    cached_appearance: Optional[str] = None  # Vision-generated, loaded from database

    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary format (for JSON serialization)."""
        result = {
            "name": self.name,
            "description": self.description,
        }
        if self.parent_name:
            result["parent_name"] = self.parent_name
        if self.appearance:
            result["appearance"] = self.appearance
        # Note: cached_appearance is NOT included (stored in database only)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scenario":
        """Create Scenario from dictionary (from JSON file)."""
        return cls(
            name=data["name"],
            description=data["description"],
            parent_name=data.get("parent_name"),
            appearance=data.get("appearance"),
            cached_appearance=None,  # Will be loaded from DB
        )
