"""
Provider Factory for LLM Provider Instantiation

Central factory for creating LLM provider instances based on configuration.
Supports automatic provider selection and validation.
"""

from typing import Optional
from core.config import LLMConfig
from core.providers.base import LLMProvider
from core.providers.openai_provider import OpenAIProvider
from core.providers.gemini_provider import GeminiProvider


class ProviderFactory:
    """
    Factory for creating LLM provider instances.

    Automatically selects and instantiates the correct provider
    based on configuration.
    """

    @staticmethod
    def create_provider(config: LLMConfig) -> LLMProvider:
        """
        Create an LLM provider instance from configuration.

        Args:
            config: LLM configuration object

        Returns:
            Initialized LLM provider instance

        Raises:
            ValueError: If provider is unknown or configuration is invalid
            ImportError: If required library for provider is not installed
        """
        provider_name = config.provider.lower()

        if provider_name == "local" or provider_name == "openai":
            # OpenAI-compatible provider (local or official)
            if not config.api_key:
                raise ValueError("LLM_API_KEY required for OpenAI provider")

            return OpenAIProvider(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model,
            )

        elif provider_name == "gemini":
            # Google Gemini provider
            if not config.gemini_api_key:
                raise ValueError("GEMINI_API_KEY required for Gemini provider")

            return GeminiProvider(
                api_key=config.gemini_api_key,
                model_name=config.gemini_model,
            )

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Supported providers: local, openai, gemini"
            )

    @staticmethod
    def list_available_providers() -> list:
        """
        List all available provider names.

        Returns:
            List of supported provider names
        """
        return ["local", "openai", "gemini"]
