"""
Visual Memory Feature - Character appearance extraction and image generation.

This feature provides:
- Visual profile extraction from reference images using Gemini Vision
- Character image generation using Imagen 3
- SQLite-based profile storage
- Platform-agnostic API (no Discord dependencies)
"""

from core.features.base_feature import BaseFeature
from core.features.visual_memory.visual_manager import VisualManager


class VisualMemoryFeature(BaseFeature):
    """
    Visual Memory feature - manages character visual profiles and image generation.

    This feature is completely independent and does NOT depend on roleplay.
    """

    @property
    def name(self) -> str:
        return "visual_memory"

    def __init__(self, config: any, db_path: str, gemini_api_key: str = None):
        """
        Initialize the visual memory feature.

        Args:
            config: Feature configuration (currently unused, reserved for future settings)
            db_path: Path to visual profiles database
            gemini_api_key: Google AI API key (reads from env if not provided)
        """
        super().__init__(config, db_path)
        self.gemini_api_key = gemini_api_key
        self.visual_manager = None

    def initialize(self, **dependencies) -> None:
        """
        Initialize the visual memory manager.

        Args:
            **dependencies: Not currently used, but available for future extensions
        """
        print("🎨 Initializing Visual Memory Feature...")

        try:
            self.visual_manager = VisualManager(
                db_path=self.db_path,
                gemini_api_key=self.gemini_api_key,
            )
            print("   ✓ Visual Memory Engine ready")
        except Exception as e:
            print(f"   ⚠ Visual Memory initialization failed: {e}")
            self.visual_manager = None

    # Convenience methods that delegate to visual_manager

    async def extract_and_save_profile(
        self, character_name: str, image_bytes: bytes
    ) -> str:
        """
        Extract visual tags from character image and save to database.

        Args:
            character_name: Name/ID of the character
            image_bytes: Raw image bytes

        Returns:
            Extracted visual tags string
        """
        if not self.visual_manager:
            raise RuntimeError("Visual Memory feature not initialized")

        return await self.visual_manager.extract_and_save_profile(
            character_name=character_name,
            image_bytes=image_bytes,
        )

    async def generate_character_image(
        self, character_name: str, action_prompt: str, aspect_ratio: str = "1:1"
    ) -> bytes:
        """
        Generate image of character using stored visual profile.

        Args:
            character_name: Name/ID of the character
            action_prompt: Description of action/scene
            aspect_ratio: Image aspect ratio (default: "1:1")

        Returns:
            Generated image bytes (PNG)
        """
        if not self.visual_manager:
            raise RuntimeError("Visual Memory feature not initialized")

        return await self.visual_manager.generate_character_image(
            character_name=character_name,
            action_prompt=action_prompt,
            aspect_ratio=aspect_ratio,
        )

    def get_visual_profile(self, character_name: str) -> str | None:
        """
        Retrieve stored visual tags for a character.

        Args:
            character_name: Name/ID of the character

        Returns:
            Visual tags string, or None if not found
        """
        if not self.visual_manager:
            raise RuntimeError("Visual Memory feature not initialized")

        return self.visual_manager.get_visual_profile(character_name)

    def list_characters(self) -> list[str]:
        """
        List all characters with visual profiles.

        Returns:
            List of character names
        """
        if not self.visual_manager:
            raise RuntimeError("Visual Memory feature not initialized")

        return self.visual_manager.list_characters()

    def delete_profile(self, character_name: str) -> bool:
        """
        Delete a character's visual profile.

        Args:
            character_name: Name/ID of the character

        Returns:
            True if deleted, False if not found
        """
        if not self.visual_manager:
            raise RuntimeError("Visual Memory feature not initialized")

        return self.visual_manager.delete_profile(character_name)

    def cleanup(self) -> None:
        """Cleanup visual memory resources."""
        print("🎨 Unloading Visual Memory Feature...")
        self.visual_manager = None
