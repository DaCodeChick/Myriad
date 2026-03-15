"""
Main scenario engine for managing hierarchical environmental contexts.

This module provides the ScenarioEngine class that coordinates scenario CRUD operations,
hierarchy management, and integrates caching and appearance generation.
"""

import json
import shutil
from pathlib import Path
from typing import Optional, List

from .scenario_models import Scenario
from .scenario_cache import ScenarioCache
from .scenario_appearance import ScenarioAppearanceGenerator


class ScenarioEngine:
    """Manages hierarchical scenario contexts (World Tree)."""

    def __init__(
        self,
        db_path: str,
        scenarios_directory: str = "scenarios",
        vision_service=None,
    ):
        """
        Initialize scenario engine.

        Args:
            db_path: Path to SQLite database file (for cached appearances and active scenario tracking)
            scenarios_directory: Directory where scenario folders are stored
            vision_service: Optional VisionCacheService for generating appearance descriptions
        """
        self.scenarios_directory = Path(scenarios_directory)
        self.scenarios_directory.mkdir(parents=True, exist_ok=True)

        # Initialize cache and appearance generator
        self.cache = ScenarioCache(db_path)
        self.appearance_generator = ScenarioAppearanceGenerator(
            vision_service=vision_service, cache=self.cache
        )

    def _get_scenario_folder_path(self, name: str) -> Path:
        """
        Get the folder path for a scenario.

        Args:
            name: Scenario name

        Returns:
            Path to scenario folder
        """
        # Sanitize name to be filesystem-safe
        safe_name = "".join(
            c for c in name if c.isalnum() or c in (" ", "_", "-")
        ).strip()
        safe_name = safe_name.replace(" ", "_").lower()

        return self.scenarios_directory / safe_name

    def _get_scenario_metadata_path(self, name: str) -> Path:
        """
        Get the metadata.json path for a scenario.

        Args:
            name: Scenario name

        Returns:
            Path to metadata.json file
        """
        return self._get_scenario_folder_path(name) / "metadata.json"

    def create_scenario(
        self, name: str, description: str, parent_name: Optional[str] = None
    ) -> Scenario:
        """
        Create a new scenario folder with metadata.json.

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
        scenario_folder = self._get_scenario_folder_path(name)
        metadata_path = self._get_scenario_metadata_path(name)

        if scenario_folder.exists():
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

        # Create folder and write metadata.json
        scenario_folder.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w", encoding="utf-8") as f:
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
        metadata_path = self._get_scenario_metadata_path(name)

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenario = Scenario.from_dict(data)
            # Load cached appearance from database (with image processing)
            scenario_folder = self._get_scenario_folder_path(name)
            scenario.cached_appearance = (
                self.appearance_generator.load_or_generate_appearance(
                    name, scenario_folder
                )
            )
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

        # Update child scenario metadata
        child.parent_name = parent_name
        metadata_path = self._get_scenario_metadata_path(child_name)
        with open(metadata_path, "w", encoding="utf-8") as f:
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

        self.cache.set_active_scenario(user_id, scenario_name)

    def get_active_scenario(self, user_id: str) -> Optional[Scenario]:
        """
        Get the currently active scenario for a user.

        Args:
            user_id: User identifier

        Returns:
            Scenario if user has an active scenario, None otherwise
        """
        scenario_name = self.cache.get_active_scenario_name(user_id)
        if scenario_name:
            return self.get_scenario(scenario_name)
        return None

    def list_all_scenarios(self) -> List[Scenario]:
        """
        List all scenarios.

        Returns:
            List of all Scenario objects
        """
        scenarios = []

        # Find all folders containing metadata.json
        for scenario_folder in sorted(self.scenarios_directory.iterdir()):
            if not scenario_folder.is_dir():
                continue

            metadata_path = scenario_folder / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                scenario = Scenario.from_dict(data)
                # Load cached appearance from database (with image processing)
                scenario.cached_appearance = (
                    self.appearance_generator.load_or_generate_appearance(
                        scenario.name, scenario_folder
                    )
                )
                scenarios.append(scenario)

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading scenario from {metadata_path}: {e}")
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

        # Delete scenario folder and all contents (metadata.json and images)
        scenario_folder = self._get_scenario_folder_path(name)
        if scenario_folder.exists():
            shutil.rmtree(scenario_folder)

        # Delete cached appearance from database
        self.cache.delete_cached_appearance(name)

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

        self.cache.update_appearance_only(name, cached_appearance)
        return True
