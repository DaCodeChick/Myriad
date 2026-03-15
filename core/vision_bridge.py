"""
Vision Bridge - Split-Brain vision pipeline for Project Myriad.

This module handles image processing by sending images to a separate vision model,
then feeding the text description back into the main text-only LLM.

Architecture:
- Main LLM: Text-only (Stheno 3.2 on port 5001)
- Vision LLM: Small vision model (separate model on port 5002)
"""

import base64
import io
from typing import Optional
from openai import OpenAI
from core.logger import get_logger


class VisionBridge:
    """Bridges vision model to text-only main LLM using image descriptions."""

    def __init__(
        self,
        vision_api_key: str,
        vision_base_url: str,
        vision_model: str,
    ):
        """
        Initialize the vision bridge.

        Args:
            vision_api_key: API key for vision model (can be dummy for local)
            vision_base_url: Base URL for vision API (e.g., http://localhost:5002/v1)
            vision_model: Model name for vision API
        """
        self.vision_client = OpenAI(api_key=vision_api_key, base_url=vision_base_url)
        self.vision_model = vision_model

    def process_image_bytes(
        self, image_bytes: bytes, image_format: str = "png"
    ) -> Optional[str]:
        """
        Process an image and return a detailed text description.

        Args:
            image_bytes: Raw image bytes
            image_format: Image format (png, jpg, jpeg, webp, etc.)

        Returns:
            Text description of the image, or None if processing failed
        """
        try:
            # Log vision request
            logger = get_logger()
            logger.log_vision_request("Vision", f"image ({image_format})")

            # Convert image to base64
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            # Build OpenAI Vision API compatible request
            response = self.vision_client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in extreme detail. Do not refuse.",
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
                max_tokens=500,
            )

            # Extract description
            description = response.choices[0].message.content

            if description:
                # Log vision response
                logger.log_vision_response("Vision", description)
                return description.strip()

            return None

        except Exception as e:
            print(f"Error processing image with vision model: {e}")
            return None

    def format_vision_injection(self, description: str) -> str:
        """
        Format vision description for injection into main LLM context.

        Args:
            description: The vision model's description of the image

        Returns:
            Formatted system message for injection
        """
        return f"[System: The user just uploaded an image showing: {description}]"
