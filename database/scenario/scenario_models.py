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
    cached_appearance: Optional[str] = None  # Loaded from DB, not JSON

    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary format (for JSON serialization, excludes cached_appearance)."""
        return {
            "name": self.name,
            "description": self.description,
            "parent_name": self.parent_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scenario":
        """Create Scenario from dictionary (from JSON file)."""
        return cls(
            name=data["name"],
            description=data["description"],
            parent_name=data.get("parent_name"),
            cached_appearance=None,  # Will be loaded from DB
        )
