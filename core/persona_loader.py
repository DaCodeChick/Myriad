"""
Persona Cartridge System - Hot-swappable personality loader for Project Myriad.

This module handles loading and validating persona metadata from the personas/
directory and its subdirectories (supporting categorization).

Each persona is a folder containing:
- metadata.json: Persona definition (system prompt, traits, relationships, etc.)
- image files: Character appearance images (automatically processed into cached descriptions)
"""

import json
import os
import hashlib
import sqlite3
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PersonaRelationship:
    """Represents a relationship override for a specific target."""

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
    cached_appearance: Optional[str] = None  # Loaded from database, not metadata.json

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
            cached_appearance=data.get("cached_appearance"),
            limbic_baseline=data.get("limbic_baseline"),
            relationships=relationships,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert persona to dictionary format (for metadata.json, excludes cached_appearance)."""
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
        # Note: cached_appearance is NOT included (stored in database)
        if self.limbic_baseline:
            result["limbic_baseline"] = self.limbic_baseline
        if self.relationships:
            result["relationships"] = [rel.to_dict() for rel in self.relationships]
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


class PersonaLoader:
    """Manages loading and caching of persona cartridges."""

    # Supported image formats for appearance generation
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

    def __init__(
        self,
        personas_dir: str = "personas",
        db_path: Optional[str] = None,
        vision_service=None,
    ):
        """
        Initialize the persona loader.

        Args:
            personas_dir: Directory containing persona folders
            db_path: Path to SQLite database (for cached appearances)
            vision_service: VisionCacheService instance for generating appearance descriptions
        """
        self.personas_dir = personas_dir
        self.db_path = db_path
        self.vision_service = vision_service
        self._cache: Dict[str, PersonaCartridge] = {}

        # Ensure personas directory exists
        os.makedirs(personas_dir, exist_ok=True)

    def load_persona(self, persona_id: str) -> Optional[PersonaCartridge]:
        """
        Load a persona cartridge from disk.

        New folder-based structure:
        - "chrono/schala" -> personas/chrono/schala/metadata.json
        - Automatically scans for image files in the persona folder
        - Generates cached appearance description if images exist and cache is stale

        Args:
            persona_id: The ID of the persona to load (can include category path)

        Returns:
            PersonaCartridge if found and valid, None otherwise
        """
        # Check cache first
        if persona_id in self._cache:
            return self._cache[persona_id]

        # Build folder path (persona_id can include subdirectories)
        persona_folder = Path(self.personas_dir) / persona_id
        metadata_path = persona_folder / "metadata.json"

        if not metadata_path.exists():
            return None

        try:
            # Load metadata.json
            with open(metadata_path, "r", encoding="utf-8") as f:
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

            # Create persona cartridge (without cached_appearance yet)
            persona = PersonaCartridge.from_dict(data)

            # Load cached appearance from database (if available)
            if self.db_path:
                cached_appearance = self._load_cached_appearance(
                    persona_id, persona_folder
                )
                persona.cached_appearance = cached_appearance

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

    def _load_cached_appearance(
        self, persona_id: str, persona_folder: Path
    ) -> Optional[str]:
        """
        Load cached appearance from database or generate if needed.

        Args:
            persona_id: The persona ID
            persona_folder: Path to the persona's folder

        Returns:
            Cached appearance description, or None if not available
        """
        if not self.db_path:
            return None

        # Find all image files in the persona folder
        image_files = self._get_image_files(persona_folder)

        if not image_files:
            return None  # No images, no appearance

        # Calculate hash of all images to detect changes
        current_hash = self._calculate_images_hash(image_files)

        # Check if we have a cached appearance and if it's still valid
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cached_appearance, image_hashes
            FROM persona_appearances
            WHERE persona_id = ?
            """,
            (persona_id,),
        )

        row = cursor.fetchone()

        if row and row[1] == current_hash:
            # Cache is valid, return it
            conn.close()
            return row[0]

        # Cache is stale or missing, need to generate new appearance
        conn.close()

        if not self.vision_service:
            return None  # Can't generate without vision service

        # Generate new appearance description
        appearance = self._generate_appearance_from_images(image_files)

        if appearance:
            # Store in database
            self._store_cached_appearance(persona_id, appearance, current_hash)

        return appearance

    def _get_image_files(self, persona_folder: Path) -> List[Path]:
        """Get all image files in a persona folder."""
        image_files = []
        for file in persona_folder.iterdir():
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
            combined = "COMBINED APPEARANCE FROM MULTIPLE IMAGES:\n\n"
            for i, desc in enumerate(descriptions, 1):
                combined += f"Image {i}: {desc}\n\n"
            return combined.strip()

    def _store_cached_appearance(
        self, persona_id: str, appearance: str, image_hash: str
    ) -> None:
        """Store cached appearance in database."""
        if not self.db_path:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO persona_appearances
            (persona_id, cached_appearance, image_hashes, last_generated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (persona_id, appearance, image_hash),
        )

        conn.commit()
        conn.close()

    def list_available_personas(self) -> List[str]:
        """
        List all available persona IDs in the personas directory (recursively).

        Looks for folders containing metadata.json files.

        Returns categorized personas with their full path:
        - "chrono/schala"
        - "generic/nsfw/alpha_stud"

        Returns:
            List of persona_id strings sorted alphabetically
        """
        if not os.path.exists(self.personas_dir):
            return []

        personas = []
        personas_path = Path(self.personas_dir)

        # Recursively find all metadata.json files
        for metadata_file in personas_path.rglob("metadata.json"):
            # Get relative path from personas directory to the folder containing metadata.json
            persona_folder = metadata_file.parent
            relative_path = persona_folder.relative_to(personas_path)
            # Convert to forward slashes for persona_id
            persona_id = str(relative_path).replace(os.sep, "/")
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

        # Build metadata.json path
        metadata_path = Path(self.personas_dir) / persona_id / "metadata.json"

        try:
            # Convert to dict and write to file with pretty formatting
            with open(metadata_path, "w", encoding="utf-8") as f:
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
        Update the cached_appearance in database (NOT in metadata.json).

        Args:
            persona_id: The ID of the persona to update
            cached_appearance: The new appearance description, or None to clear it

        Returns:
            True if successful, False if persona doesn't exist or update failed
        """
        if not self.db_path:
            return False

        # Load the persona first to ensure it exists
        persona = self.load_persona(persona_id)
        if not persona:
            return False

        # Update the cached_appearance in database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if cached_appearance:
                # Store new appearance
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO persona_appearances
                    (persona_id, cached_appearance, image_hashes, last_generated)
                    VALUES (?, ?, '', CURRENT_TIMESTAMP)
                    """,
                    (persona_id, cached_appearance),
                )
            else:
                # Clear appearance
                cursor.execute(
                    "DELETE FROM persona_appearances WHERE persona_id = ?",
                    (persona_id,),
                )

            conn.commit()
            conn.close()

            # Update cached persona object
            persona.cached_appearance = cached_appearance
            self._cache[persona_id] = persona

            return True

        except Exception as e:
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
        Create a new persona folder with metadata.json.

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
        persona_folder = Path(self.personas_dir) / persona_id
        if persona_folder.exists():
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
            # Create persona folder
            persona_folder.mkdir(parents=True, exist_ok=True)

            # Write metadata.json with pretty formatting
            metadata_path = persona_folder / "metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(persona.to_dict(), f, indent=2, ensure_ascii=False)

            # Cache it
            self._cache[persona_id] = persona

            return True

        except (OSError, ValueError) as e:
            print(f"Error creating persona '{persona_id}': {e}")
            return False
