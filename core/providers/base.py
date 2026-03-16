"""
Base LLM Provider Interface

Abstract base class that all LLM providers must implement.
Ensures consistent API across different backends (OpenAI, Gemini, Anthropic, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement the generate() method to ensure
    a consistent interface across different LLM backends.
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.9,
        max_tokens: int = 500,
    ) -> Optional[str]:
        """
        Generate a response from the LLM.

        Args:
            messages: Conversation history in OpenAI format
                     [{"role": "system|user|assistant", "content": "..."}]
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response string, or None on error
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier (e.g., 'gpt-4', 'gemini-1.5-pro')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'gemini')."""
        pass
