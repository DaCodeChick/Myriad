"""
Vision processing for Discord image attachments.

Handles downloading and processing image attachments through the Vision Bridge.
"""

from typing import Optional

import discord

from core.vision_bridge import VisionBridge


class VisionProcessor:
    """Processes image attachments from Discord messages through Vision Bridge."""

    def __init__(self, vision_bridge: Optional[VisionBridge] = None):
        """
        Initialize vision processor.

        Args:
            vision_bridge: Optional VisionBridge for processing images
        """
        self.vision_bridge = vision_bridge

    async def process_attachments(self, message: discord.Message) -> Optional[str]:
        """
        Process image attachments from a Discord message.

        Args:
            message: Discord message containing attachments

        Returns:
            Vision description if an image was processed, None otherwise
        """
        if not message.attachments or not self.vision_bridge:
            return None

        for attachment in message.attachments:
            # Check if attachment is an image
            if attachment.content_type and attachment.content_type.startswith("image/"):
                try:
                    # Download image bytes
                    image_bytes = await attachment.read()

                    # Extract image format from content type
                    image_format = attachment.content_type.split("/")[-1]

                    # Process through vision bridge
                    description = self.vision_bridge.process_image_bytes(
                        image_bytes, image_format
                    )

                    if description:
                        print(f"[Vision] Processed image: {description[:100]}...")
                        return description  # Only process first image

                except Exception as e:
                    print(f"[Vision] Error processing attachment: {e}")

        return None
