"""
Scenario appearance generation from images.

This module handles image processing and AI-generated appearance descriptions
for scenarios using the Vision API.
"""

import hashlib
from pathlib import Path
from typing import Optional, List


# Supported image formats for appearance generation
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


class ScenarioAppearanceGenerator:
    """Generates appearance descriptions from scenario images using Vision API."""

    def __init__(self, vision_service=None, cache=None):
        """
        Initialize appearance generator.

        Args:
            vision_service: Optional VisionCacheService for generating descriptions
            cache: ScenarioCache instance for storing/retrieving cached appearances
        """
        self.vision_service = vision_service
        self.cache = cache

    def get_image_files(self, scenario_folder: Path) -> List[Path]:
        """
        Get all image files in a scenario folder.

        Args:
            scenario_folder: Path to the scenario folder

        Returns:
            Sorted list of image file paths
        """
        image_files = []
        for file in scenario_folder.iterdir():
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
                image_files.append(file)
        return sorted(image_files)  # Sort for consistent hashing

    def calculate_images_hash(self, image_files: List[Path]) -> str:
        """
        Calculate combined hash of all image files.

        Args:
            image_files: List of image file paths

        Returns:
            SHA256 hash of all images combined
        """
        hasher = hashlib.sha256()

        for image_file in image_files:
            # Hash filename and content
            hasher.update(image_file.name.encode())
            with open(image_file, "rb") as f:
                hasher.update(f.read())

        return hasher.hexdigest()

    def generate_from_images(self, image_files: List[Path]) -> Optional[str]:
        """
        Generate appearance description from multiple images using Vision API.

        Args:
            image_files: List of image file paths

        Returns:
            Combined appearance description, or None if generation failed
        """
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
                    image_bytes, image_format, persona_name="Scenario"
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

    def load_or_generate_appearance(
        self,
        scenario_name: str,
        scenario_folder: Path,
        fallback_appearance: Optional[str] = None,
    ) -> Optional[str]:
        """
        Load cached appearance or generate new one if cache is stale.

        Falls back to manually-defined appearance from JSON if no images exist
        or vision generation fails.

        Args:
            scenario_name: Name of the scenario
            scenario_folder: Path to the scenario folder
            fallback_appearance: Manual appearance from metadata.json to use as fallback

        Returns:
            Appearance description, or fallback, or None if not available
        """
        if not scenario_folder.exists():
            return fallback_appearance

        # Find all image files in the scenario folder
        image_files = self.get_image_files(scenario_folder)

        if not image_files:
            # No images, use fallback appearance from JSON
            return fallback_appearance

        # Calculate hash of all images to detect changes
        current_hash = self.calculate_images_hash(image_files)

        # Check if we have a cached appearance and if it's still valid
        if self.cache:
            cached_data = self.cache.get_cached_appearance(scenario_name)
            if cached_data:
                cached_appearance, cached_hash = cached_data
                if cached_hash == current_hash:
                    # Cache is valid, return it
                    return cached_appearance

        # Cache is stale or missing, need to generate new appearance
        if not self.vision_service:
            # Can't generate without vision service, use fallback
            return fallback_appearance

        # Generate new appearance description
        appearance = self.generate_from_images(image_files)

        if appearance and self.cache:
            # Store in database
            self.cache.store_cached_appearance(scenario_name, appearance, current_hash)
            return appearance

        # Vision generation failed, use fallback
        return fallback_appearance
