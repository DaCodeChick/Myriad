"""
Scenario Engine (World Tree) for Project Myriad.

This module manages hierarchical environmental contexts stored as JSON files,
allowing the AI to understand nested locations and world states
(e.g., a room within a building within a city within an era).

The system uses a parent-child relationship structure where scenarios can be nested infinitely.
Cached appearances are stored in SQLite for AI-generated visual descriptions.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


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


class ScenarioEngine:
    """Manages hierarchical scenario contexts (World Tree)."""

    def __init__(self, db_path: str, scenarios_directory: str = "scenarios"):
        """
        Initialize scenario engine.

        Args:
            db_path: Path to SQLite database file (for cached appearances and active scenario tracking)
            scenarios_directory: Directory where scenario JSON files are stored
        """
        self.db_path = db_path
        self.scenarios_directory = Path(scenarios_directory)
        self.scenarios_directory.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Ensure cached appearance and active scenario tables exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create table for storing cached appearances (AI-generated visual descriptions)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_appearances (
                scenario_name TEXT PRIMARY KEY,
                cached_appearance TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Add active_scenario_name column to user_state if it doesn't exist
        cursor.execute("PRAGMA table_info(user_state)")
        columns = [row[1] for row in cursor.fetchall()]

        if "active_scenario_name" not in columns:
            cursor.execute(
                """
                ALTER TABLE user_state 
                ADD COLUMN active_scenario_name TEXT
            """
            )

        conn.commit()
        conn.close()

    def _get_scenario_file_path(self, name: str) -> Path:
        """Get the file path for a scenario JSON file."""
        # Sanitize name to be filesystem-safe
        safe_name = "".join(
            c for c in name if c.isalnum() or c in (" ", "_", "-")
        ).strip()
        safe_name = safe_name.replace(" ", "_").lower()

        return self.scenarios_directory / f"{safe_name}.json"

    def _load_cached_appearance(self, name: str) -> Optional[str]:
        """Load cached appearance from database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cached_appearance 
            FROM scenario_appearances 
            WHERE scenario_name = ?
        """,
            (name,),
        )

        row = cursor.fetchone()
        conn.close()

        return row["cached_appearance"] if row else None

    def create_scenario(
        self, name: str, description: str, parent_name: Optional[str] = None
    ) -> Scenario:
        """
        Create a new scenario.

        Args:
            name: Unique name for the scenario
            description: Detailed description of this scenario/location
            parent_name: Optional name of parent scenario to nest this within

        Returns:
            The created Scenario object

        Raises:
            FileExistsError: If a scenario with this name already exists
            ValueError: If parent_name doesn't exist
        """
        scenario_path = self._get_scenario_file_path(name)

        if scenario_path.exists():
            raise FileExistsError(f"Scenario '{name}' already exists")

        # Verify parent exists if specified
        if parent_name:
            parent = self.get_scenario(parent_name)
            if not parent:
                raise ValueError(f"Parent scenario '{parent_name}' does not exist")

        scenario = Scenario(
            name=name,
            description=description,
            parent_name=parent_name,
        )

        # Write to JSON file
        with open(scenario_path, "w", encoding="utf-8") as f:
            json.dump(scenario.to_dict(), f, indent=2, ensure_ascii=False)

        return scenario

    def get_scenario(self, name: str) -> Optional[Scenario]:
        """
        Get a scenario by name.

        Args:
            name: Name of the scenario

        Returns:
            Scenario if found, None otherwise
        """
        scenario_path = self._get_scenario_file_path(name)

        if not scenario_path.exists():
            return None

        try:
            with open(scenario_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenario = Scenario.from_dict(data)
            # Load cached appearance from database
            scenario.cached_appearance = self._load_cached_appearance(name)
            return scenario

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading scenario {name}: {e}")
            return None

    def get_scenario_hierarchy(self, name: str) -> List[Scenario]:
        """
        Get the full hierarchy from root to the specified scenario.

        Args:
            name: Name of the scenario to get hierarchy for

        Returns:
            List of Scenario objects from root (index 0) to target scenario (last index)
        """
        scenario = self.get_scenario(name)
        if not scenario:
            return []

        hierarchy = [scenario]

        # Walk up the tree
        current = scenario
        while current.parent_name:
            parent = self.get_scenario(current.parent_name)
            if not parent:
                break  # Broken link in hierarchy
            hierarchy.insert(0, parent)
            current = parent

        return hierarchy

    def set_parent(self, child_name: str, parent_name: str) -> None:
        """
        Set or update the parent of a scenario.

        Args:
            child_name: Name of the scenario to modify
            parent_name: Name of the new parent scenario

        Raises:
            ValueError: If child or parent doesn't exist, or if it would create a cycle
        """
        child = self.get_scenario(child_name)
        if not child:
            raise ValueError(f"Child scenario '{child_name}' does not exist")

        parent = self.get_scenario(parent_name)
        if not parent:
            raise ValueError(f"Parent scenario '{parent_name}' does not exist")

        # Check for cycles: the parent's hierarchy shouldn't contain the child
        parent_hierarchy = self.get_scenario_hierarchy(parent_name)
        if any(s.name == child_name for s in parent_hierarchy):
            raise ValueError(
                f"Cannot set '{parent_name}' as parent of '{child_name}': would create a cycle"
            )

        # Update child scenario
        child.parent_name = parent_name
        scenario_path = self._get_scenario_file_path(child_name)
        with open(scenario_path, "w", encoding="utf-8") as f:
            json.dump(child.to_dict(), f, indent=2, ensure_ascii=False)

    def set_active_scenario(self, user_id: str, scenario_name: Optional[str]) -> None:
        """
        Set the active scenario for a user.

        Args:
            user_id: User identifier
            scenario_name: Name of the scenario to activate, or None to clear

        Raises:
            ValueError: If scenario_name doesn't exist
        """
        if scenario_name and not self.get_scenario(scenario_name):
            raise ValueError(f"Scenario '{scenario_name}' does not exist")

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_state (user_id, active_scenario_name)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET active_scenario_name = excluded.active_scenario_name
        """,
            (user_id, scenario_name),
        )

        conn.commit()
        conn.close()

    def get_active_scenario(self, user_id: str) -> Optional[Scenario]:
        """
        Get the currently active scenario for a user.

        Args:
            user_id: User identifier

        Returns:
            Scenario if user has an active scenario, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT active_scenario_name FROM user_state WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row and row["active_scenario_name"]:
            return self.get_scenario(row["active_scenario_name"])

        return None

    def list_all_scenarios(self) -> List[Scenario]:
        """
        List all scenarios.

        Returns:
            List of all Scenario objects
        """
        scenarios = []

        for scenario_file in sorted(self.scenarios_directory.glob("*.json")):
            try:
                with open(scenario_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                scenario = Scenario.from_dict(data)
                # Load cached appearance from database
                scenario.cached_appearance = self._load_cached_appearance(scenario.name)
                scenarios.append(scenario)

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading scenario from {scenario_file}: {e}")
                continue

        return scenarios

    def delete_scenario(self, name: str) -> None:
        """
        Delete a scenario.

        Args:
            name: Name of the scenario to delete

        Raises:
            ValueError: If scenario doesn't exist or has children
        """
        scenario = self.get_scenario(name)
        if not scenario:
            raise ValueError(f"Scenario '{name}' does not exist")

        # Check if any scenarios have this as a parent
        all_scenarios = self.list_all_scenarios()
        children = [s for s in all_scenarios if s.parent_name == name]

        if children:
            child_names = ", ".join(s.name for s in children)
            raise ValueError(
                f"Cannot delete '{name}': it has child scenarios ({child_names}). "
                f"Delete or reparent them first."
            )

        # Delete JSON file
        scenario_path = self._get_scenario_file_path(name)
        scenario_path.unlink()

        # Delete cached appearance from database
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM scenario_appearances WHERE scenario_name = ?", (name,)
        )
        conn.commit()
        conn.close()

    def update_scenario_appearance(
        self, name: str, cached_appearance: Optional[str]
    ) -> bool:
        """
        Update the cached_appearance field of an existing scenario.

        Args:
            name: Name of the scenario to update
            cached_appearance: New appearance description, or None to clear

        Returns:
            True if updated, False if scenario not found
        """
        scenario = self.get_scenario(name)
        if not scenario:
            return False

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO scenario_appearances (scenario_name, cached_appearance)
            VALUES (?, ?)
            ON CONFLICT(scenario_name) DO UPDATE SET 
                cached_appearance = excluded.cached_appearance,
                updated_at = CURRENT_TIMESTAMP
        """,
            (name, cached_appearance),
        )

        conn.commit()
        conn.close()

        return True
