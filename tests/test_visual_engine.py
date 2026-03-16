"""
Test script for Visual Memory Engine.

This demonstrates the platform-agnostic API without Discord.
"""

import asyncio
from core.features.visual_memory import VisualManager


async def main():
    """Test Visual Memory Engine functionality."""
    print("🧪 Testing Visual Memory Engine\n")

    # Initialize manager
    try:
        visual_manager = VisualManager(db_path="data/visual_profiles_test.db")
        print("✅ Visual Manager initialized\n")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # Test: List characters (should be empty)
    print("📋 Listing characters...")
    characters = visual_manager.list_characters()
    print(f"   Found {len(characters)} characters: {characters}\n")

    # Test: Extract visual profile from sample image
    print("🔍 Testing visual profile extraction...")
    print("   (Requires a test image at 'test_character.png')\n")

    try:
        with open("test_character.png", "rb") as f:
            image_bytes = f.read()

        visual_tags = await visual_manager.extract_and_save_profile(
            character_name="test_char", image_bytes=image_bytes
        )

        print(f"✅ Extracted visual profile:")
        print(f"   {visual_tags}\n")

    except FileNotFoundError:
        print("⚠ Skipping extraction test - test_character.png not found\n")
    except Exception as e:
        print(f"❌ Extraction failed: {e}\n")

    # Test: Retrieve visual profile
    print("📖 Testing profile retrieval...")
    profile = visual_manager.get_visual_profile("test_char")
    if profile:
        print(f"✅ Retrieved profile: {profile[:100]}...\n")
    else:
        print("⚠ No profile found\n")

    # Test: Generate character image
    if profile:
        print("🎨 Testing image generation...")
        try:
            image_bytes = await visual_manager.generate_character_image(
                character_name="test_char",
                action_prompt="standing confidently",
                aspect_ratio="1:1",
            )

            # Save generated image
            with open("test_output.png", "wb") as f:
                f.write(image_bytes)

            print(f"✅ Generated image saved to test_output.png")
            print(f"   Size: {len(image_bytes)} bytes\n")

        except Exception as e:
            print(f"❌ Generation failed: {e}\n")

    # Test: List characters again
    print("📋 Listing characters after tests...")
    characters = visual_manager.list_characters()
    print(f"   Found {len(characters)} characters: {characters}\n")

    # Test: Delete profile
    if "test_char" in characters:
        print("🗑️ Testing profile deletion...")
        deleted = visual_manager.delete_profile("test_char")
        if deleted:
            print("✅ Profile deleted successfully\n")
        else:
            print("❌ Deletion failed\n")

    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
