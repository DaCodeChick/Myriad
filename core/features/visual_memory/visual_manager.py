"""
Visual Memory Engine - Character appearance extraction and image generation.

CRITICAL: This module MUST NOT import discord or any platform-specific code.
It is a pure data/API layer for visual character profiles.

Features:
- Extract visual tags from character reference images using Gemini Vision
- Store character visual profiles in SQLite database
- Generate character images using Imagen 3 with stored visual tags
"""

import sqlite3
import os
from typing import Optional, Tuple, List
from pathlib import Path


class VisualManager:
    """
    Manages character visual profiles and image generation.

    This class is platform-agnostic and does NOT import discord.
    """

    def __init__(
        self,
        db_path: str = "data/visual_profiles.db",
        gemini_api_key: Optional[str] = None,
    ):
        """
        Initialize Visual Manager.

        Args:
            db_path: Path to SQLite database file
            gemini_api_key: Google AI API key (reads from GEMINI_API_KEY env if not provided)
        """
        self.db_path = db_path

        # Get API key from environment if not provided
        self.api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY environment variable "
                "or pass gemini_api_key parameter."
            )

        # Lazy import to avoid ImportError if library not installed
        try:
            from google import genai
            from google.genai import types

            self.genai = genai
            self.types = types
            self.client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "google-genai library not installed. "
                "Install with: pip install google-genai"
            )

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with visual_profiles table."""
        # Ensure data directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Create table if not exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visual_profiles (
                character_name TEXT PRIMARY KEY,
                visual_tags TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    async def extract_and_save_profile(
        self, character_name: str, image_bytes: bytes
    ) -> str:
        """
        Extract visual tags from character image and save to database.

        Uses Gemini Vision to analyze the image and generate a comprehensive
        list of visual tags describing the character's appearance.

        Args:
            character_name: Name/ID of the character (case-insensitive)
            image_bytes: Raw image bytes (PNG, JPG, WEBP, etc.)

        Returns:
            The extracted visual tags as a comma-separated string

        Raises:
            Exception: If vision extraction fails or API error occurs
        """
        # Normalize character name (lowercase for consistency)
        character_name = character_name.lower().strip()

        # CRITICAL: Apply BLOCK_NONE safety settings so it doesn't censor suggestive art
        safety_settings = [
            self.types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"
            ),
            self.types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"
            ),
            self.types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"
            ),
            self.types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"
            ),
        ]

        # Construct the vision analysis prompt
        prompt = (
            "Analyze this character. Write an exhaustive, comma-separated list of "
            "visual tags describing their physical appearance, hair style/color, eye color, "
            "clothing, and distinct features. Do not describe the background, pose, or expression. "
            "Only output the core aesthetic tags."
        )

        try:
            # Create multimodal content with image
            contents = [
                self.types.Content(
                    role="user",
                    parts=[
                        self.types.Part(
                            text=prompt,
                        ),
                        self.types.Part(
                            inline_data=self.types.Blob(
                                mime_type="image/png",  # Gemini auto-detects format
                                data=image_bytes,
                            )
                        ),
                    ],
                )
            ]

            # Generate analysis using Gemini Vision
            response = await self.client.aio.models.generate_content(
                model="gemini-1.5-pro",  # Use latest vision model
                contents=contents,
                config=self.types.GenerateContentConfig(
                    temperature=0.5,  # Lower temperature for consistent extraction
                    safety_settings=safety_settings,
                ),
            )

            # Extract text from response
            if not response.text:
                raise ValueError(
                    "Gemini returned empty response - image may be filtered"
                )

            visual_tags = response.text.strip()

            # Save to database (upsert)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO visual_profiles (character_name, visual_tags, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(character_name) DO UPDATE SET
                    visual_tags = excluded.visual_tags,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (character_name, visual_tags),
            )

            conn.commit()
            conn.close()

            return visual_tags

        except Exception as e:
            raise Exception(f"Failed to extract visual profile: {str(e)}")

    async def generate_character_image(
        self, character_name: str, action_prompt: str, aspect_ratio: str = "1:1"
    ) -> bytes:
        """
        Generate image of character performing action using stored visual tags.

        Retrieves character's visual tags from database, combines with action prompt,
        and generates image using Imagen 3.

        Args:
            character_name: Name/ID of the character (case-insensitive)
            action_prompt: Description of action/scene (e.g., "standing in a forest")
            aspect_ratio: Image aspect ratio (default: "1:1")
                         Options: "1:1", "16:9", "9:16", "4:3", "3:4"

        Returns:
            Raw generated image bytes (PNG format)

        Raises:
            ValueError: If character has no visual profile saved
            Exception: If image generation fails
        """
        # Normalize character name
        character_name = character_name.lower().strip()

        # Retrieve visual tags from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT visual_tags FROM visual_profiles WHERE character_name = ?",
            (character_name,),
        )

        result = cursor.fetchone()
        conn.close()

        if not result:
            raise ValueError(
                f"No visual profile found for character '{character_name}'. "
                f"Use extract_and_save_profile() first to create one."
            )

        visual_tags = result[0]

        # Construct final prompt with quality tags
        final_prompt = f"{visual_tags}, {action_prompt}, masterpiece, best quality"

        try:
            # Configure image generation
            config = self.types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                include_rai_reason=True,
                safety_filter_level="block_only_high",  # Allow mature content
                add_watermark=False,
                output_mime_type="image/png",
            )

            # Generate image using Imagen 3
            response = await self.client.aio.models.generate_images(
                model="imagen-3.0-generate-001",
                prompt=final_prompt,
                config=config,
            )

            # Extract image bytes
            if not response.generated_images:
                raise ValueError("No images were generated - prompt may be filtered")

            gen_img = response.generated_images[0]

            # Check if filtered
            if gen_img.rai_filtered_reason:
                raise ValueError(
                    f"Image was filtered for safety: {gen_img.rai_filtered_reason}"
                )

            # Return image bytes
            if gen_img.image and gen_img.image.image_bytes:
                return gen_img.image.image_bytes
            else:
                raise ValueError("Generated image has no data")

        except Exception as e:
            raise Exception(f"Failed to generate character image: {str(e)}")

    def get_visual_profile(self, character_name: str) -> Optional[str]:
        """
        Retrieve stored visual tags for a character.

        Args:
            character_name: Name/ID of the character (case-insensitive)

        Returns:
            Visual tags string, or None if not found
        """
        character_name = character_name.lower().strip()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT visual_tags FROM visual_profiles WHERE character_name = ?",
            (character_name,),
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def list_characters(self) -> List[str]:
        """
        List all characters with visual profiles.

        Returns:
            List of character names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT character_name FROM visual_profiles ORDER BY character_name"
        )
        results = cursor.fetchall()
        conn.close()

        return [row[0] for row in results]

    def delete_profile(self, character_name: str) -> bool:
        """
        Delete a character's visual profile.

        Args:
            character_name: Name/ID of the character (case-insensitive)

        Returns:
            True if deleted, False if not found
        """
        character_name = character_name.lower().strip()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM visual_profiles WHERE character_name = ?",
            (character_name,),
        )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted
