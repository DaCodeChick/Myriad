"""
Appearance generator using Vision API integration.

Handles generating cached appearance descriptions from persona image files
using the vision service.
"""

import hashlib
from pathlib import Path
from typing import List, Optional


class AppearanceGenerator:
    """Generates appearance descriptions from persona images using vision service."""

    # Supported image formats for appearance generation
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

    def __init__(self, vision_service=None):
        """
        Initialize the appearance generator.

        Args:
            vision_service: VisionCacheService instance for generating appearance descriptions
        """
        self.vision_service = vision_service

    def get_image_files(self, persona_folder: Path) -> List[Path]:
        """
        Get all image files in a persona folder.

        Args:
            persona_folder: Path to the persona's folder

        Returns:
            Sorted list of image file paths
        """
        image_files = []
        for file in persona_folder.iterdir():
            if file.is_file() and file.suffix.lower() in self.IMAGE_EXTENSIONS:
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
        Generate appearance description from multiple images.

        Args:
            image_files: List of image file paths to process

        Returns:
            Generated appearance description, or None if generation failed
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
