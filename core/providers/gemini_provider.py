"""
Gemini Provider for Project Myriad

Google Gemini API provider with complete safety override for uncensored roleplay.
All harm categories are set to BLOCK_NONE to allow mature content.
"""

from typing import List, Dict, Optional

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
    ) -> Optional[str]:
        """
        Generate a response using Gemini API with safety overrides.

        Args:
            messages: Conversation history in OpenAI format
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response string, or None on error
        """
        try:
            # Initialize model with safety overrides
            model = genai.GenerativeModel(
                model_name=self._model_name,
                safety_settings=self.safety_settings,
            )

            # Convert chat history to Gemini format
            gemini_history = self._convert_to_gemini_format(messages)

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
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, any]]:
        """
        Convert OpenAI-style chat history to Gemini format.

        Gemini format:
        - Uses 'user' and 'model' roles (not 'assistant')
        - System prompts are prepended as first user message
        - Messages have 'role' and 'parts' keys (parts is a list of strings)

        Args:
            messages: OpenAI-style chat history

        Returns:
            Gemini-formatted chat history
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
        for msg in messages:
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

            gemini_history.append(
                {
                    "role": gemini_role,
                    "parts": [content],
                }
            )

        return gemini_history

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        return self._model_name

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gemini"
