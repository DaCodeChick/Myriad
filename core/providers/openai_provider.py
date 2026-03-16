"""
OpenAI-Compatible Provider

Provider implementation for OpenAI API and OpenAI-compatible endpoints
(e.g., local models via KoboldCPP, LM Studio, text-generation-webui, etc.)
"""

from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI

from core.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    OpenAI-compatible API provider.

    Works with:
    - Official OpenAI API (GPT-4, GPT-3.5, etc.)
    - Local models via OpenAI-compatible servers:
      - KoboldCPP
      - LM Studio
      - text-generation-webui (oobabooga)
      - vLLM
      - Ollama (with OpenAI compatibility mode)
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        """
        Initialize OpenAI provider.

        Args:
            api_key: API key (use "not-needed" for local servers)
            base_url: API endpoint (e.g., "https://api.openai.com/v1" or "http://localhost:5001/v1")
            model: Model identifier
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model_name = model
        self._base_url = base_url

        print(f"✅ OpenAI provider initialized: {model} @ {base_url}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.9,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Generate a response using OpenAI-compatible API.

        Args:
            messages: Conversation history in OpenAI format
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters (ignored)

        Returns:
            Generated response string, or None on error
        """
        try:
            response = await self.client.chat.completions.create(
                model=self._model_name,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            return content if content else None

        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return None

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        return self._model_name

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        if "openai.com" in self._base_url:
            return "openai"
        else:
            return "openai-compatible"
