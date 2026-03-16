"""
Gemini API Engine for Project Myriad

Provides Google Gemini integration with complete safety override for uncensored roleplay.
Uses official google-generativeai library with BLOCK_NONE on all harm categories.
"""

import os
from typing import List, Dict, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. Run: pip install google-generativeai")


class GeminiEngine:
    """
    Google Gemini API wrapper with safety overrides for uncensored roleplay.

    CRITICAL: All safety filters are disabled (BLOCK_NONE) to allow mature content.
    This is intentional for Project Myriad's uncensored roleplay use case.
    """

    def __init__(
        self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-pro"
    ):
        """
        Initialize Gemini engine with API credentials.

        Args:
            api_key: Google AI API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (default: gemini-1.5-pro)

        Raises:
            ValueError: If API key not provided and not in environment
            ImportError: If google-generativeai library not installed
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai library not installed. "
                "Install with: pip install google-generativeai"
            )

        # Load API key from parameter or environment
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set in .env or pass to constructor."
            )

        # Configure API client
        genai.configure(api_key=self.api_key)

        # Store model name
        self.model_name = model_name

        # CRITICAL: Safety settings - DISABLE ALL FILTERS for uncensored roleplay
        # This allows mature, sexual, violent, and otherwise restricted content
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        print(f"✅ Gemini engine initialized: {model_name} (Safety filters: DISABLED)")

    async def generate_response(
        self,
        system_prompt: str,
        chat_history: List[Dict[str, str]],
        temperature: float = 0.9,
        max_tokens: int = 500,
    ) -> Optional[str]:
        """
        Generate a response using Gemini API with safety overrides.

        Args:
            system_prompt: System instructions for the model
            chat_history: List of message dicts with 'role' and 'content' keys
                         Expected roles: 'user', 'assistant', 'system'
            temperature: Sampling temperature (0.0-2.0, default 0.9)
            max_tokens: Maximum tokens to generate (default 500)

        Returns:
            Generated response string, or None on error

        Notes:
            - Gemini doesn't have native 'system' role, so system_prompt is prepended as user message
            - OpenAI-style chat_history is converted to Gemini's format
            - Safety filters are DISABLED (BLOCK_NONE) for all harm categories
        """
        try:
            # Initialize model with safety overrides
            model = genai.GenerativeModel(
                model_name=self.model_name,
                safety_settings=self.safety_settings,
            )

            # Convert chat history to Gemini format
            # Gemini uses 'user' and 'model' roles (not 'assistant')
            gemini_history = self._convert_chat_history(system_prompt, chat_history)

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

    def _convert_chat_history(
        self, system_prompt: str, chat_history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Convert OpenAI-style chat history to Gemini format.

        Gemini format:
        - Uses 'user' and 'model' roles (not 'assistant')
        - System prompts are prepended as first user message
        - Messages have 'role' and 'parts' keys (parts is a list of strings)

        Args:
            system_prompt: System instructions to prepend
            chat_history: OpenAI-style chat history

        Returns:
            Gemini-formatted chat history
        """
        gemini_history = []

        # Prepend system prompt as first user message
        # This ensures Gemini receives context/instructions
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
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Skip empty messages
            if not content:
                continue

            # Convert role names
            if role == "assistant":
                gemini_role = "model"
            elif role == "system":
                # Inject system messages as user messages
                gemini_role = "user"
            else:
                gemini_role = "user"

            gemini_history.append(
                {
                    "role": gemini_role,
                    "parts": [content],
                }
            )

        return gemini_history


async def generate_gemini_response(
    system_prompt: str,
    chat_history: List[Dict[str, str]],
    temperature: float = 0.9,
    max_tokens: int = 500,
    api_key: Optional[str] = None,
    model_name: str = "gemini-1.5-pro",
) -> Optional[str]:
    """
    Convenience function for one-off Gemini API calls.

    Creates a new GeminiEngine instance and generates a response.
    For repeated calls, instantiate GeminiEngine directly to reuse configuration.

    Args:
        system_prompt: System instructions for the model
        chat_history: List of message dicts with 'role' and 'content' keys
        temperature: Sampling temperature (0.0-2.0, default 0.9)
        max_tokens: Maximum tokens to generate (default 500)
        api_key: Optional API key (defaults to GEMINI_API_KEY env var)
        model_name: Model to use (default: gemini-1.5-pro)

    Returns:
        Generated response string, or None on error

    Example:
        >>> response = await generate_gemini_response(
        ...     system_prompt="You are a helpful assistant.",
        ...     chat_history=[
        ...         {"role": "user", "content": "Hello!"},
        ...         {"role": "assistant", "content": "Hi there!"},
        ...         {"role": "user", "content": "How are you?"},
        ...     ],
        ...     temperature=0.9,
        ...     max_tokens=500,
        ... )
    """
    engine = GeminiEngine(api_key=api_key, model_name=model_name)
    return await engine.generate_response(
        system_prompt=system_prompt,
        chat_history=chat_history,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# Synchronous wrapper for backward compatibility
def generate_gemini_response_sync(
    system_prompt: str,
    chat_history: List[Dict[str, str]],
    temperature: float = 0.9,
    max_tokens: int = 500,
    api_key: Optional[str] = None,
    model_name: str = "gemini-1.5-pro",
) -> Optional[str]:
    """
    Synchronous wrapper for generate_gemini_response.

    Note: This creates an event loop if one doesn't exist.
    Prefer using the async version in async contexts.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        generate_gemini_response(
            system_prompt=system_prompt,
            chat_history=chat_history,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            model_name=model_name,
        )
    )
