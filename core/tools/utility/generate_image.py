"""
Generate Image tool - Create images using Gemini's Imagen 3 model.

Provides AI agents with image generation capabilities via Google's Imagen 3.
Returns generated image data that can be sent to Discord as attachments.
"""

from typing import Dict, Any, Optional, List, Tuple
from core.tools.base import Tool


class GenerateImageTool(Tool):
    """Tool for generating images using Gemini's Imagen 3 model."""

    @property
    def name(self) -> str:
        return "generate_image"

    @property
    def description(self) -> str:
        return (
            "Generate images from text descriptions using Imagen 3. Use this when "
            "the user asks you to create, draw, generate, make, or visualize an image. "
            "Returns image data that will be sent to the user as an attachment."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed description of the image to generate. "
                        "Be specific about subject, style, composition, colors, lighting, etc."
                    ),
                },
                "negative_prompt": {
                    "type": "string",
                    "description": (
                        "Optional: Things to avoid in the image "
                        "(e.g., 'blurry, low quality, distorted')"
                    ),
                },
                "aspect_ratio": {
                    "type": "string",
                    "description": (
                        "Image aspect ratio. Options: '1:1' (square), '16:9' (landscape), "
                        "'9:16' (portrait), '4:3', '3:4'. Default: '1:1'"
                    ),
                },
                "number_of_images": {
                    "type": "integer",
                    "description": "Number of images to generate (1-4). Default: 1",
                },
            },
            "required": ["prompt"],
        }

    async def execute_async(self, **kwargs) -> Dict[str, Any]:
        """
        Generate images asynchronously using Gemini's Imagen 3.

        Args:
            prompt: Text description of the image to generate
            negative_prompt: Optional things to avoid
            aspect_ratio: Image aspect ratio (default: '1:1')
            number_of_images: Number of images to generate (default: 1)

        Returns:
            Dict with:
                - success: bool
                - message: str (user-facing message)
                - images: List[Tuple[bytes, str]] (image_bytes, mime_type)
                - metadata: Dict with generation details
        """
        prompt = kwargs.get("prompt", "")
        negative_prompt = kwargs.get("negative_prompt")
        aspect_ratio = kwargs.get("aspect_ratio", "1:1")
        number_of_images = min(kwargs.get("number_of_images", 1), 4)

        if not prompt:
            return {
                "success": False,
                "message": "Error: No image description provided",
                "images": [],
            }

        # Get Gemini client from context
        gemini_client = None
        if self.context.llm_provider:
            # Check if it's a Gemini provider with the client attribute
            if hasattr(self.context.llm_provider, "client"):
                gemini_client = self.context.llm_provider.client

        if not gemini_client:
            return {
                "success": False,
                "message": (
                    "Image generation is only available with Gemini provider. "
                    "Please set LLM_PROVIDER=gemini in your .env file."
                ),
                "images": [],
            }

        try:
            from google.genai import types

            # Configure image generation
            config = types.GenerateImagesConfig(
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                include_rai_reason=True,  # Include safety filter reasons
                safety_filter_level="block_only_high",  # Allow most content
                add_watermark=False,  # No watermark for Discord
                output_mime_type="image/png",  # PNG for quality
            )

            # Generate images
            response = await gemini_client.aio.models.generate_images(
                model="imagen-3.0-generate-001",  # Imagen 3 model
                prompt=prompt,
                config=config,
            )

            # Extract generated images
            if not response.generated_images:
                return {
                    "success": False,
                    "message": "No images were generated. The prompt may have been filtered for safety.",
                    "images": [],
                }

            # Collect image data
            images: List[Tuple[bytes, str]] = []
            filtered_count = 0

            for gen_img in response.generated_images:
                # Check if filtered
                if gen_img.rai_filtered_reason:
                    filtered_count += 1
                    continue

                # Extract image bytes
                if gen_img.image and gen_img.image.image_bytes:
                    mime_type = gen_img.image.mime_type or "image/png"
                    images.append((gen_img.image.image_bytes, mime_type))

            # Build result message
            if not images:
                return {
                    "success": False,
                    "message": (
                        f"All {filtered_count} generated image(s) were filtered for safety. "
                        "Try adjusting your prompt to be more appropriate."
                    ),
                    "images": [],
                }

            # Success
            message = f"Generated {len(images)} image(s) for: '{prompt[:50]}...'"
            if filtered_count > 0:
                message += f" ({filtered_count} filtered)"

            return {
                "success": True,
                "message": message,
                "images": images,
                "metadata": {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "aspect_ratio": aspect_ratio,
                    "requested": number_of_images,
                    "generated": len(images),
                    "filtered": filtered_count,
                },
            }

        except ImportError:
            return {
                "success": False,
                "message": (
                    "Image generation unavailable: google-genai library not installed. "
                    "Install with: pip install google-genai"
                ),
                "images": [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error generating image: {str(e)}",
                "images": [],
            }

    def execute(self, **kwargs) -> str:
        """
        Synchronous wrapper - not supported for image generation.

        Image generation requires async execution. This returns an error message.
        """
        return (
            "Error: Image generation requires async execution. "
            "This tool must be called through execute_async()."
        )

    def can_execute(self) -> bool:
        """Check if image generation is available."""
        if not self.context.llm_provider:
            return False
        # Only available if we have a Gemini provider with a client
        return (
            hasattr(self.context.llm_provider, "client")
            and hasattr(self.context.llm_provider, "provider_name")
            and self.context.llm_provider.provider_name == "gemini"
        )
