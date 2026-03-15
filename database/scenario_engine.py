"""
Scenario Engine (World Tree) for Project Myriad.

This module manages hierarchical environmental contexts stored as folder-based scenarios,
allowing the AI to understand nested locations and world states
(e.g., a room within a building within a city within an era).

Each scenario is a folder containing:
- metadata.json: Scenario definition (name, description, parent_name)
- Image files (optional): Automatically processed into cached appearance descriptions

The system uses a parent-child relationship structure where scenarios can be nested infinitely.
Cached appearances are stored in SQLite for AI-generated visual descriptions.
"""

import sqlite3
import json
import os
import hashlib
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

    # Supported image formats for appearance generation
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

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
        self.db_path = db_path
        self.scenarios_directory = Path(scenarios_directory)
        self.scenarios_directory.mkdir(parents=True, exist_ok=True)
        self.vision_service = vision_service
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
                last_generated TEXT DEFAULT CURRENT_TIMESTAMP,
                image_hashes TEXT
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

    def _get_scenario_folder_path(self, name: str) -> Path:
        """Get the folder path for a scenario."""
        # Sanitize name to be filesystem-safe
        safe_name = "".join(
            c for c in name if c.isalnum() or c in (" ", "_", "-")
        ).strip()
        safe_name = safe_name.replace(" ", "_").lower()

        return self.scenarios_directory / safe_name

    def _get_scenario_metadata_path(self, name: str) -> Path:
        """Get the metadata.json path for a scenario."""
        return self._get_scenario_folder_path(name) / "metadata.json"

    def _load_cached_appearance(self, name: str) -> Optional[str]:
        """Load cached appearance from database or generate if needed."""
        scenario_folder = self._get_scenario_folder_path(name)

        if not scenario_folder.exists():
            return None

        # Find all image files in the scenario folder
        image_files = self._get_image_files(scenario_folder)

        if not image_files:
            return None  # No images, no appearance

        # Calculate hash of all images to detect changes
        current_hash = self._calculate_images_hash(image_files)

        # Check if we have a cached appearance and if it's still valid
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cached_appearance, image_hashes 
            FROM scenario_appearances 
            WHERE scenario_name = ?
        """,
            (name,),
        )

        row = cursor.fetchone()

        if row and row["image_hashes"] == current_hash:
            # Cache is valid, return it
            conn.close()
            return row["cached_appearance"]

        # Cache is stale or missing, need to generate new appearance
        conn.close()

        if not self.vision_service:
            return None  # Can't generate without vision service

        # Generate new appearance description
        appearance = self._generate_appearance_from_images(image_files)

        if appearance:
            # Store in database
            self._store_cached_appearance(name, appearance, current_hash)

        return appearance

    def _get_image_files(self, scenario_folder: Path) -> List[Path]:
        """Get all image files in a scenario folder."""
        image_files = []
        for file in scenario_folder.iterdir():
            if file.is_file() and file.suffix.lower() in self.IMAGE_EXTENSIONS:
                image_files.append(file)
        return sorted(image_files)  # Sort for consistent hashing

    def _calculate_images_hash(self, image_files: List[Path]) -> str:
        """Calculate combined hash of all image files."""
        hasher = hashlib.sha256()

        for image_file in image_files:
            # Hash filename and content
            hasher.update(image_file.name.encode())
            with open(image_file, "rb") as f:
                hasher.update(f.read())

        return hasher.hexdigest()

    def _generate_appearance_from_images(
        self, image_files: List[Path]
    ) -> Optional[str]:
        """Generate appearance description from multiple images."""
        if not self.vision_service:
            return None

        descriptions = []

        for image_file in image_files:
            try:
                with open(image_file, "rb") as f:
                    image_bytes = f.read()

                # Determine image format from extension
                image_format = image_file.suffix.lower().lstrip(".")

                # Generate description for this image
                description = self.vision_service.generate_appearance_description(
                    image_bytes, image_format
                )

                if description:
                    descriptions.append(description)

            except Exception as e:
                print(f"Error processing image {image_file}: {e}")

        if not descriptions:
            return None

        # If multiple descriptions, combine them
        if len(descriptions) == 1:
            return descriptions[0]
        else:
            # Concatenate with separators
            combined = "COMBINED VISUAL DESCRIPTION FROM MULTIPLE IMAGES:\n\n"
            for i, desc in enumerate(descriptions, 1):
                combined += f"Image {i}: {desc}\n\n"
            return combined.strip()

    def _store_cached_appearance(
        self, name: str, appearance: str, image_hash: str
    ) -> None:
        """Store cached appearance in database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO scenario_appearances
            (scenario_name, cached_appearance, image_hashes, last_generated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (name, appearance, image_hash),
        )

        conn.commit()
        conn.close()

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
                scenario.cached_appearance = self._load_cached_appearance(scenario.name)
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
            import shutil

            shutil.rmtree(scenario_folder)

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
