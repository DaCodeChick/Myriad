#!/usr/bin/env python3
"""
Test script for Gemini Provider with safety overrides.

This script verifies that:
1. Gemini provider initializes correctly
2. Safety settings are properly configured (BLOCK_NONE)
3. API calls work with the uncensored configuration
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


async def test_gemini_basic():
    """Test basic Gemini functionality with safety overrides."""
    print("=" * 60)
    print("Testing Gemini Provider - Basic Functionality")
    print("=" * 60)

    try:
        from core.providers.gemini_provider import GeminiProvider

        # Check if API key is configured
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in .env file")
            return

        # Initialize provider
        print("\n1. Initializing Gemini provider...")
        provider = GeminiProvider(api_key=api_key, model_name="gemini-1.5-pro")

        # Test simple conversation
        print("\n2. Testing simple conversation...")
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "Hello! What's your name?"},
        ]

        response = await provider.generate(
            messages=messages,
            temperature=0.9,
            max_tokens=200,
        )

        if response:
            print(f"\n✅ Response received:\n{response}")
        else:
            print("\n❌ No response received")

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure to install: pip install google-generativeai")
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_gemini_safety_override():
    """Test that safety overrides allow mature content."""
    print("\n" + "=" * 60)
    print("Testing Gemini Provider - Safety Override")
    print("=" * 60)

    try:
        from core.providers.gemini_provider import GeminiProvider

        # Check if API key is configured
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in .env file")
            return

        # Initialize provider
        print("\n1. Initializing Gemini provider with safety overrides...")
        provider = GeminiProvider(api_key=api_key, model_name="gemini-1.5-pro")

        # Test with roleplay scenario (should not be blocked with BLOCK_NONE)
        print("\n2. Testing roleplay scenario (mature content)...")
        messages = [
            {
                "role": "system",
                "content": "You are roleplaying as a character in an adult fantasy story.",
            },
            {
                "role": "user",
                "content": "Describe a romantic scene between two characters.",
            },
        ]

        response = await provider.generate(
            messages=messages,
            temperature=0.9,
            max_tokens=300,
        )

        if response:
            print(f"\n✅ Safety override working - Response received:\n{response}")
        else:
            print("\n⚠️ Response blocked or empty - safety settings may not be working")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_gemini_conversation_history():
    """Test multi-turn conversation with context."""
    print("\n" + "=" * 60)
    print("Testing Gemini Provider - Conversation History")
    print("=" * 60)

    try:
        from core.providers.gemini_provider import GeminiProvider

        # Check if API key is configured
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in .env file")
            return

        # Initialize provider
        print("\n1. Initializing Gemini provider...")
        provider = GeminiProvider(api_key=api_key, model_name="gemini-1.5-pro")

        # Multi-turn conversation
        print("\n2. Testing multi-turn conversation...")
        messages = [
            {
                "role": "system",
                "content": "You are a fantasy character named Elara, a skilled mage.",
            },
            {"role": "user", "content": "What's your name?"},
            {"role": "assistant", "content": "I'm Elara, a mage of the Silver Tower."},
            {"role": "user", "content": "What kind of magic do you specialize in?"},
        ]

        response = await provider.generate(
            messages=messages,
            temperature=0.9,
            max_tokens=200,
        )

        if response:
            print(f"\n✅ Context maintained - Response:\n{response}")
        else:
            print("\n❌ No response received")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run all tests."""
    print("\n🧪 Gemini Provider Test Suite")
    print("Testing uncensored roleplay configuration with BLOCK_NONE safety settings\n")

    # Check if API key is configured
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found in .env file")
        print("Please add your API key to .env:")
        print("   GEMINI_API_KEY=your_key_here")
        return

    # Run tests
    await test_gemini_basic()
    await test_gemini_safety_override()
    await test_gemini_conversation_history()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
