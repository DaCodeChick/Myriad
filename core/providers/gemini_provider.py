"""
Gemini Provider for Project Myriad

Google Gemini API provider with complete safety override for uncensored roleplay.
All harm categories are set to BLOCK_NONE to allow mature content.

FEATURES:
- Text generation with safety overrides
- Multimodal vision (image analysis)
- Support for PNG, JPG, WEBP, GIF, HEIC images
"""

import mimetypes
from typing import List, Dict, Optional, Tuple, Any

from core.providers.base import LLMProvider

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    HarmCategory = None
    HarmBlockThreshold = None


class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider with safety overrides.

    CRITICAL: All safety filters are disabled (BLOCK_NONE) to allow mature content.
    This is intentional for Project Myriad's uncensored roleplay use case.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        """
        Initialize Gemini provider with API credentials.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-1.5-pro)

        Raises:
            ImportError: If google-generativeai library not installed
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai library not installed. "
                "Install with: pip install google-generativeai"
            )

        # Configure API client
        genai.configure(api_key=api_key)

        # Store model name
        self._model_name = model_name

        # CRITICAL: Safety settings - DISABLE ALL FILTERS for uncensored roleplay
        # This allows mature, sexual, violent, and otherwise restricted content
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        print(
            f"✅ Gemini provider initialized: {model_name} (Safety filters: DISABLED)"
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.9,
        max_tokens: int = 500,
        image_data: Optional[List[Tuple[bytes, str]]] = None,
    ) -> Optional[str]:
        """
        Generate a response using Gemini API with safety overrides.

        Supports multimodal vision - can analyze images alongside text prompts.

        Args:
            messages: Conversation history in OpenAI format
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            image_data: Optional list of (image_bytes, mime_type) tuples for vision
                       Example: [(png_bytes, "image/png"), (jpg_bytes, "image/jpeg")]

        Returns:
            Generated response string, or None on error

        Example with images:
            >>> image_bytes = open("photo.jpg", "rb").read()
            >>> response = await provider.generate(
            ...     messages=[{"role": "user", "content": "What's in this image?"}],
            ...     image_data=[(image_bytes, "image/jpeg")]
            ... )
        """
        try:
            # Initialize model with safety overrides
            model = genai.GenerativeModel(
                model_name=self._model_name,
                safety_settings=self.safety_settings,
            )

            # Convert chat history to Gemini format
            gemini_history = self._convert_to_gemini_format(messages, image_data)

            # Configure generation parameters
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Start chat session with history
            chat = model.start_chat(history=gemini_history[:-1])  # All but last message

            # Send last message and get response
            last_message = gemini_history[-1]["parts"]
            response = await chat.send_message_async(
                last_message,
                generation_config=generation_config,
                safety_settings=self.safety_settings,  # Re-apply safety overrides
            )

            # Extract text from response
            if response and response.text:
                return response.text
            else:
                print("⚠️ Gemini returned empty response")
                return None

        except Exception as e:
            print(f"❌ Gemini API error: {e}")
            return None

    def _convert_to_gemini_format(
        self,
        messages: List[Dict[str, str]],
        image_data: Optional[List[Tuple[bytes, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convert OpenAI-style chat history to Gemini format with optional image support.

        Gemini format:
        - Uses 'user' and 'model' roles (not 'assistant')
        - System prompts are prepended as first user message
        - Messages have 'role' and 'parts' keys (parts is a list)
        - Images are added as Part objects with inline_data

        Args:
            messages: OpenAI-style chat history
            image_data: Optional list of (image_bytes, mime_type) tuples

        Returns:
            Gemini-formatted chat history with embedded images

        Notes:
            - Images are attached to the last user message
            - Supported formats: image/png, image/jpeg, image/webp, image/gif, image/heic
            - Safety overrides (BLOCK_NONE) apply to image content as well
        """
        gemini_history = []
        system_prompt = None

        # Extract system prompt if present
        for msg in messages:
            if msg.get("role") == "system" and not system_prompt:
                system_prompt = msg.get("content", "")
                break

        # Prepend system prompt as first user message
        if system_prompt:
            gemini_history.append(
                {
                    "role": "user",
                    "parts": [system_prompt],
                }
            )
            # Add empty model response to establish conversation pattern
            gemini_history.append(
                {
                    "role": "model",
                    "parts": ["Understood. I will follow these instructions."],
                }
            )

        # Convert chat history messages
        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Skip system messages (already handled above) and empty messages
            if role == "system" or not content:
                continue

            # Convert role names
            if role == "assistant":
                gemini_role = "model"
            else:
                gemini_role = "user"

            # Build parts list (text + optional images)
            # Parts can be strings (text) or dicts (inline_data for images)
            parts: List[Any] = [content]

            # Attach images to the LAST user message (if this is it and images provided)
            is_last_message = i == len(messages) - 1
            if gemini_role == "user" and is_last_message and image_data:
                # Add image parts using Gemini's inline_data format
                for img_bytes, mime_type in image_data:
                    image_part = {
                        "inline_data": {"mime_type": mime_type, "data": img_bytes}
                    }
                    parts.append(image_part)

                print(
                    f"📸 Added {len(image_data)} image(s) to Gemini request (safety: BLOCK_NONE)"
                )

            gemini_history.append(
                {
                    "role": gemini_role,
                    "parts": parts,
                }
            )

        return gemini_history

    @staticmethod
    def detect_image_mime_type(
        image_bytes: bytes, filename: Optional[str] = None
    ) -> str:
        """
        Detect MIME type for image bytes.

        Args:
            image_bytes: Raw image data
            filename: Optional filename for extension-based detection

        Returns:
            MIME type string (e.g., "image/jpeg", "image/png")

        Notes:
            - Checks magic bytes (file signature) for accurate detection
            - Falls back to filename extension if provided
            - Defaults to "image/jpeg" if detection fails
        """
        # Check magic bytes (file signatures)
        if len(image_bytes) >= 8:
            # PNG signature
            if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
                return "image/png"
            # JPEG signature
            elif image_bytes[:2] == b"\xff\xd8":
                return "image/jpeg"
            # GIF signature
            elif image_bytes[:6] in (b"GIF87a", b"GIF89a"):
                return "image/gif"
            # WEBP signature
            elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
                return "image/webp"

        # Fallback to filename extension
        if filename:
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type and mime_type.startswith("image/"):
                return mime_type

        # Default to JPEG
        return "image/jpeg"

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        return self._model_name

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gemini"
