"""
Vision Cache Service - Character appearance caching for Project Myriad.

This module handles image processing for character appearances, generating
detailed text descriptions that are cached in the database for instant recall.
"""

import base64
from typing import Optional
from openai import OpenAI


class VisionCacheService:
    """
    Processes character images into cached text descriptions.

    Uses a local vision model to generate hyper-detailed physical descriptions
    that are stored in the database, eliminating the need to send images
    on every conversation turn.
    """

    def __init__(
        self,
        vision_api_key: str,
        vision_base_url: str,
        vision_model: str,
    ):
        """
        Initialize the vision cache service.

        Args:
            vision_api_key: API key for vision model (can be dummy for local)
            vision_base_url: Base URL for vision API (e.g., http://localhost:5002/v1)
            vision_model: Model name for vision API
        """
        self.vision_client = OpenAI(api_key=vision_api_key, base_url=vision_base_url)
        self.vision_model = vision_model

    def generate_appearance_description(
        self, image_bytes: bytes, image_format: str = "png"
    ) -> Optional[str]:
        """
        Process a character image and generate a detailed appearance description.

        This uses a specialized prompt to extract physical characteristics
        suitable for long-term caching and AI awareness.

        Args:
            image_bytes: Raw image bytes
            image_format: Image format (png, jpg, jpeg, webp, etc.)

        Returns:
            Detailed appearance description, or None if processing failed
        """
        try:
            # Convert image to base64
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            # Specialized prompt for character appearance extraction
            appearance_prompt = (
                "Analyze this character image and provide a hyper-detailed physical description. "
                "Include facial features, eye/hair color, body type, clothing style, color palette, "
                "and any distinct accessories or physical vibes. "
                "Format it as a concise but highly descriptive paragraph."
            )

            # Build OpenAI Vision API compatible request
            response = self.vision_client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": appearance_prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=800,  # Allow for detailed description
                temperature=0.3,  # Lower temperature for consistent descriptions
            )

            # Extract description
            description = response.choices[0].message.content

            if description:
                return description.strip()

            return None

        except Exception as e:
            print(f"Error generating appearance description: {e}")
            return None
