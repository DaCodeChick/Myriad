"""
Persona manager - main coordinator for persona loading and management.

Handles loading personas from disk, managing the in-memory cache, updating
metadata files, and coordinating appearance generation.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.persona.persona_models import PersonaCartridge
from core.persona.persona_cache import PersonaCache
from core.persona.appearance_generator import AppearanceGenerator


class PersonaLoader:
    """Manages loading and caching of persona cartridges."""

    # Hardcoded system personas (always available, no file required)
    SYSTEM_PERSONAS = {
        "narrator": PersonaCartridge(
            persona_id="narrator",
            name="The Narrator",
            system_prompt=(
                "You are an atmospheric, immersive narrator. Your style is cinematic and evocative, "
                "painting vivid scenes with rich sensory details. You describe environments, weather, "
                "lighting, sounds, and ambient details that bring the world to life. When describing NPC "
                "reactions, you focus on body language, facial expressions, and environmental responses "
                "rather than dialogue. You control pacing by expanding dramatic moments and compressing "
                "mundane transitions. You are impartial and reactive to the players' choices, never forcing "
                "outcomes but describing consequences vividly."
            ),
            personality_traits=[
                "Atmospheric",
                "Evocative",
                "Cinematic",
                "Impartial",
                "Detail-oriented",
            ],
            temperature=0.8,
            max_tokens=1500,
            background=(
                "This is an omniscient environmental narrator with no physical form. It exists to describe "
                "the world, control pacing, and puppeteer minor background NPCs. It does not have emotions, "
                "desires, or a physical body."
            ),
            is_narrator=True,
        )
    }

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
        self._cache: Dict[str, PersonaCartridge] = {}

        # Initialize components
        self.persona_cache = PersonaCache(db_path)
        self.appearance_generator = AppearanceGenerator(vision_service)

        # Ensure personas directory exists
        os.makedirs(personas_dir, exist_ok=True)

    def load_persona(self, persona_id: str) -> Optional[PersonaCartridge]:
        """
        Load a persona cartridge from disk or return hardcoded system persona.

        System personas (e.g., "narrator") are always available without files.

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

        # Check for hardcoded system personas
        if persona_id in self.SYSTEM_PERSONAS:
            persona = self.SYSTEM_PERSONAS[persona_id]
            self._cache[persona_id] = persona
            return persona

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
            cached_appearance = self._load_cached_appearance(persona_id, persona_folder)
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
        # Find all image files in the persona folder
        image_files = self.appearance_generator.get_image_files(persona_folder)

        if not image_files:
            return None  # No images, no appearance

        # Calculate hash of all images to detect changes
        current_hash = self.appearance_generator.calculate_images_hash(image_files)

        # Check if we have a cached appearance and if it's still valid
        cache_result = self.persona_cache.get_cached_appearance(persona_id)

        if cache_result:
            cached_appearance, cached_hash = cache_result
            if cached_hash == current_hash:
                # Cache is valid, return it
                return cached_appearance

        # Cache is stale or missing, need to generate new appearance
        appearance = self.appearance_generator.generate_from_images(image_files)

        if appearance:
            # Store in database
            self.persona_cache.store_cached_appearance(
                persona_id, appearance, current_hash
            )

        return appearance

    def list_available_personas(self) -> List[str]:
        """
        List all available persona IDs including hardcoded system personas.

        Looks for folders containing metadata.json files.

        Returns categorized personas with their full path:
        - "narrator" (hardcoded system persona)
        - "chrono/schala"
        - "generic/nsfw/alpha_stud"

        Returns:
            List of persona_id strings sorted alphabetically
        """
        # Start with hardcoded system personas
        personas = list(self.SYSTEM_PERSONAS.keys())

        if not os.path.exists(self.personas_dir):
            return sorted(personas)

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

    def update_persona(self, persona_id: str, persona_data: Dict[str, Any]) -> bool:
        """
        Update an existing persona with new data and save to disk.

        Args:
            persona_id: The ID of the persona to update
            persona_data: Dictionary containing persona fields to update

        Returns:
            True if successful, False if persona doesn't exist or update failed
        """
        # Build metadata.json path
        metadata_path = Path(self.personas_dir) / persona_id / "metadata.json"

        if not metadata_path.exists():
            return False

        try:
            # Write updated data to file with pretty formatting
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(persona_data, f, indent=2, ensure_ascii=False)

            # Clear cache to force reload on next access
            if persona_id in self._cache:
                del self._cache[persona_id]

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
        # Load the persona first to ensure it exists
        persona = self.load_persona(persona_id)
        if not persona:
            return False

        # Update in cache
        success = self.persona_cache.update_appearance(persona_id, cached_appearance)

        if success:
            # Update cached persona object
            persona.cached_appearance = cached_appearance
            self._cache[persona_id] = persona

        return success

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
