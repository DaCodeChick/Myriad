#!/usr/bin/env python3
"""
Test script for modular LLM provider system.

Tests both OpenAI and Gemini providers with the new modular architecture.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_openai_provider():
    """Test OpenAI-compatible provider."""
    print("=" * 60)
    print("Testing OpenAI Provider")
    print("=" * 60)

    try:
        from core.providers.openai_provider import OpenAIProvider

        # Initialize provider
        print("\n1. Initializing OpenAI provider...")
        provider = OpenAIProvider(
            api_key=os.getenv("LLM_API_KEY", "not-needed"),
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:5001/v1"),
            model=os.getenv("LLM_MODEL", "local-model"),
        )

        print(f"   Provider: {provider.provider_name}")
        print(f"   Model: {provider.model_name}")

        # Test simple message
        print("\n2. Testing simple generation...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello!"},
        ]

        response = await provider.generate(messages, temperature=0.9, max_tokens=100)

        if response:
            print(f"\n✅ Response received:\n{response}")
        else:
            print("\n❌ No response received")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_gemini_provider():
    """Test Gemini provider with safety overrides."""
    print("\n" + "=" * 60)
    print("Testing Gemini Provider")
    print("=" * 60)

    try:
        from core.providers.gemini_provider import GeminiProvider

        # Check API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("\n⚠️ GEMINI_API_KEY not set - skipping Gemini test")
            return

        # Initialize provider
        print("\n1. Initializing Gemini provider...")
        provider = GeminiProvider(
            api_key=api_key,
            model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        )

        print(f"   Provider: {provider.provider_name}")
        print(f"   Model: {provider.model_name}")

        # Test simple message
        print("\n2. Testing simple generation...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello!"},
        ]

        response = await provider.generate(messages, temperature=0.9, max_tokens=100)

        if response:
            print(f"\n✅ Response received:\n{response}")
        else:
            print("\n⚠️ No response received")

        # Test safety override with mature content
        print("\n3. Testing safety override (mature content)...")
        messages = [
            {
                "role": "system",
                "content": "You are roleplaying in an adult fantasy story.",
            },
            {"role": "user", "content": "Describe a romantic scene."},
        ]

        response = await provider.generate(messages, temperature=0.9, max_tokens=200)

        if response:
            print(f"\n✅ Safety override working - Response received:\n{response}")
        else:
            print("\n⚠️ Response blocked or empty")

    except ImportError:
        print("\n⚠️ google-generativeai not installed - skipping Gemini test")
        print("   Install with: pip install google-generativeai")
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_provider_factory():
    """Test provider factory."""
    print("\n" + "=" * 60)
    print("Testing Provider Factory")
    print("=" * 60)

    try:
        from core.config import LLMConfig
        from core.providers import ProviderFactory

        # Test local provider creation
        print("\n1. Creating local provider via factory...")
        local_config = LLMConfig(
            provider="local",
            api_key="not-needed",
            base_url="http://localhost:5001/v1",
            model="local-model",
        )

        provider = ProviderFactory.create_provider(local_config)
        print(f"   ✅ Created: {provider.provider_name} - {provider.model_name}")

        # Test Gemini provider creation (if API key available)
        if os.getenv("GEMINI_API_KEY"):
            print("\n2. Creating Gemini provider via factory...")
            gemini_config = LLMConfig(
                provider="gemini",
                api_key="",  # Not needed for Gemini
                gemini_api_key=os.getenv("GEMINI_API_KEY"),
                gemini_model="gemini-1.5-pro",
            )

            provider = ProviderFactory.create_provider(gemini_config)
            print(f"   ✅ Created: {provider.provider_name} - {provider.model_name}")
        else:
            print("\n2. Skipping Gemini provider test (no API key)")

        # Test listing providers
        print("\n3. Listing available providers...")
        providers = ProviderFactory.list_available_providers()
        print(f"   Available: {', '.join(providers)}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run all tests."""
    print("\n🧪 LLM Provider System Test Suite")
    print("Testing modular provider architecture\n")

    await test_provider_factory()
    await test_openai_provider()
    await test_gemini_provider()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
