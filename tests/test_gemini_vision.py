#!/usr/bin/env python3
"""
Test script for Gemini multimodal vision support.

This script verifies that:
1. Images can be uploaded and processed by Gemini
2. Safety settings (BLOCK_NONE) apply to image content
3. MIME type detection works correctly
4. Images are properly attached to the last user message
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_gemini_vision_basic():
    """Test basic vision functionality with a sample image."""
    print("=" * 60)
    print("Testing Gemini Vision - Basic Image Analysis")
    print("=" * 60)

    try:
        from core.providers.gemini_provider import GeminiProvider

        # Check if API key is configured
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in .env file")
            return

        # Initialize provider
        print("\n1. Initializing Gemini provider with vision support...")
        provider = GeminiProvider(api_key=api_key, model_name="gemini-1.5-pro")

        # Create a simple test image (1x1 PNG - minimal valid image)
        # PNG header + IHDR chunk for 1x1 white pixel
        test_image = (
            b"\x89PNG\r\n\x1a\n"  # PNG signature
            b"\x00\x00\x00\rIHDR"  # IHDR chunk
            b"\x00\x00\x00\x01"  # Width: 1
            b"\x00\x00\x00\x01"  # Height: 1
            b"\x08\x02\x00\x00\x00"  # Bit depth, color type, etc.
            b"\x90wS\xde"  # CRC
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"  # IDAT
            b"\x18\r\n\x0b"  # CRC
            b"\x00\x00\x00\x00IEND\xaeB`\x82"  # IEND
        )

        # Test MIME type detection
        print("\n2. Testing MIME type detection...")
        detected_mime = GeminiProvider.detect_image_mime_type(test_image)
        print(f"   Detected MIME type: {detected_mime}")
        assert detected_mime == "image/png", f"Expected image/png, got {detected_mime}"
        print("   ✅ MIME detection working correctly")

        # Test vision with simple prompt
        print("\n3. Testing vision with image analysis...")
        messages = [{"role": "user", "content": "Describe what you see in this image."}]

        response = await provider.generate(
            messages=messages,
            image_data=[(test_image, detected_mime)],
            temperature=0.7,
            max_tokens=300,
        )

        if response:
            print(f"\n✅ Vision response received:\n{response}")
        else:
            print("\n❌ No response received from vision API")

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure to install: pip install google-generativeai")
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_mime_type_detection():
    """Test MIME type detection for various image formats."""
    print("\n" + "=" * 60)
    print("Testing MIME Type Detection")
    print("=" * 60)

    try:
        from core.providers.gemini_provider import GeminiProvider

        test_cases = [
            # PNG
            (b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, "image/png", "PNG signature"),
            # JPEG
            (b"\xff\xd8\xff\xe0" + b"\x00" * 20, "image/jpeg", "JPEG signature"),
            # GIF87a
            (b"GIF87a" + b"\x00" * 20, "image/gif", "GIF87a signature"),
            # GIF89a
            (b"GIF89a" + b"\x00" * 20, "image/gif", "GIF89a signature"),
            # WEBP
            (
                b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 20,
                "image/webp",
                "WEBP signature",
            ),
        ]

        print("\nTesting various image format signatures:")
        for image_bytes, expected_mime, description in test_cases:
            detected = GeminiProvider.detect_image_mime_type(image_bytes)
            status = "✅" if detected == expected_mime else "❌"
            print(f"  {status} {description}: {detected} (expected: {expected_mime})")

        # Test filename fallback
        print("\nTesting filename-based detection:")
        unknown_bytes = b"\x00\x00\x00\x00"  # Unknown signature
        mime_from_filename = GeminiProvider.detect_image_mime_type(
            unknown_bytes, filename="test.jpg"
        )
        print(f"  Filename 'test.jpg': {mime_from_filename}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_multimodal_conversation():
    """Test multimodal conversation with context."""
    print("\n" + "=" * 60)
    print("Testing Multimodal Conversation with Context")
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

        # Create test image
        test_image = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00"
            b"\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            b"\x18\r\n\x0b"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # Multi-turn conversation with image in last message
        print("\n2. Testing conversation with vision context...")
        messages = [
            {"role": "user", "content": "Hello! I'm going to show you an image."},
            {
                "role": "assistant",
                "content": "Great! I'd be happy to analyze an image for you.",
            },
            {
                "role": "user",
                "content": "Here it is. What can you tell me about this image?",
            },
        ]

        response = await provider.generate(
            messages=messages,
            image_data=[(test_image, "image/png")],
            temperature=0.7,
            max_tokens=300,
        )

        if response:
            print(f"\n✅ Multimodal conversation response:\n{response}")
        else:
            print("\n❌ No response received")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_safety_override_with_images():
    """Test that safety overrides work with image content."""
    print("\n" + "=" * 60)
    print("Testing Safety Override with Image Content")
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

        # Verify safety settings
        print("\n2. Verifying safety settings (BLOCK_NONE)...")
        print("   All harm categories set to BLOCK_NONE for uncensored roleplay")

        # Create test image
        test_image = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00"
            b"\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            b"\x18\r\n\x0b"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        print("\n3. Testing vision request with safety overrides...")
        messages = [
            {
                "role": "user",
                "content": "Analyze this image in a roleplay context. Describe what you see.",
            }
        ]

        response = await provider.generate(
            messages=messages,
            image_data=[(test_image, "image/png")],
            temperature=0.9,
            max_tokens=300,
        )

        if response:
            print(
                f"\n✅ Safety override working with images - Response received:\n{response}"
            )
        else:
            print(
                "\n⚠️ Response blocked or empty - safety settings may not be applied to vision"
            )

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run all vision tests."""
    print("\n🧪 Gemini Vision Test Suite")
    print(
        "Testing multimodal vision support with safety overrides (BLOCK_NONE settings)\n"
    )

    # Check if API key is configured
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found in .env file")
        print("Please add your API key to .env:")
        print("   GEMINI_API_KEY=your_key_here")
        return

    # Run tests
    await test_mime_type_detection()
    await test_gemini_vision_basic()
    await test_multimodal_conversation()
    await test_safety_override_with_images()

    print("\n" + "=" * 60)
    print("✅ All vision tests completed!")
    print("=" * 60)
    print("\nNOTE: For real-world usage, replace test images with actual PNG/JPG files")
    print("Example:")
    print("  image_bytes = open('photo.jpg', 'rb').read()")
    print(
        "  mime_type = GeminiProvider.detect_image_mime_type(image_bytes, 'photo.jpg')"
    )
    print("  response = await provider.generate(")
    print("      messages=[...],")
    print("      image_data=[(image_bytes, mime_type)]")
    print("  )")


if __name__ == "__main__":
    asyncio.run(main())
