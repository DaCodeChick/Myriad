#!/usr/bin/env python3
"""
Test script for the Metacognition Engine (Internal Thought Tracking).

This test suite validates:
1. Thought saving and retrieval
2. Per user+persona pair isolation
3. Thought ordering (most recent first)
4. Thought clearing functionality
5. Thought extraction regex patterns
6. Thought formatting (inline vs. terminal-only)
"""

import os
import sys
import tempfile
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.metacognition_engine import MetacognitionEngine


def test_save_and_retrieve_thought():
    """Test that thoughts can be saved and retrieved."""
    print("\n1. Testing save and retrieve thought...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = MetacognitionEngine(db_path=db_path)
        user_id = "test_user_1"
        persona_id = "test_persona_1"
        thought = "The user seems anxious. I should offer reassurance."

        # Save thought
        engine.save_thought(user_id, persona_id, thought)

        # Retrieve thought
        retrieved = engine.get_previous_thought(user_id, persona_id)

        assert retrieved == thought
        print(f"   ✓ Thought saved and retrieved: '{thought}'")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_per_user_persona_isolation():
    """Test that thoughts are isolated per user+persona pair."""
    print("\n2. Testing per user+persona isolation...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = MetacognitionEngine(db_path=db_path)

        # Save different thoughts for different user+persona pairs
        engine.save_thought("user1", "persona1", "Thought A")
        engine.save_thought("user1", "persona2", "Thought B")
        engine.save_thought("user2", "persona1", "Thought C")

        # Retrieve and verify isolation
        thought_a = engine.get_previous_thought("user1", "persona1")
        thought_b = engine.get_previous_thought("user1", "persona2")
        thought_c = engine.get_previous_thought("user2", "persona1")

        assert thought_a == "Thought A"
        assert thought_b == "Thought B"
        assert thought_c == "Thought C"
        print("   ✓ Thoughts correctly isolated per user+persona pair")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_most_recent_thought_returned():
    """Test that the most recent thought is returned when multiple exist."""
    print("\n3. Testing most recent thought retrieval...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = MetacognitionEngine(db_path=db_path)
        user_id = "test_user_3"
        persona_id = "test_persona_1"

        # Save multiple thoughts
        engine.save_thought(user_id, persona_id, "First thought")
        engine.save_thought(user_id, persona_id, "Second thought")
        engine.save_thought(user_id, persona_id, "Third thought")

        # Get previous thought (should be most recent)
        retrieved = engine.get_previous_thought(user_id, persona_id)

        assert retrieved == "Third thought"
        print("   ✓ Most recent thought retrieved correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_clear_thoughts():
    """Test that thoughts can be cleared for a user+persona pair."""
    print("\n4. Testing clear thoughts...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = MetacognitionEngine(db_path=db_path)
        user_id = "test_user_4"
        persona_id = "test_persona_1"

        # Save thought
        engine.save_thought(user_id, persona_id, "Some thought")

        # Verify thought exists
        assert engine.get_previous_thought(user_id, persona_id) == "Some thought"

        # Clear thoughts
        engine.clear_thoughts(user_id, persona_id)

        # Verify thought is cleared
        assert engine.get_previous_thought(user_id, persona_id) is None

        print("   ✓ Thoughts cleared successfully")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_thought_extraction_regex():
    """Test regex pattern for extracting thoughts from responses."""
    print("\n5. Testing thought extraction regex...")

    try:
        # Test single-line thought
        response1 = "<thought>Planning my approach</thought>\nHello there!"
        match1 = re.search(r"<thought>(.*?)</thought>", response1, re.DOTALL)
        assert match1 is not None
        assert match1.group(1).strip() == "Planning my approach"

        # Test multi-line thought
        response2 = """<thought>
The user seems anxious.
My serotonin is elevated.
I should offer reassurance.
</thought>
Here's my actual response."""
        match2 = re.search(r"<thought>(.*?)</thought>", response2, re.DOTALL)
        assert match2 is not None
        thought = match2.group(1).strip()
        assert "The user seems anxious" in thought
        assert "I should offer reassurance" in thought

        # Test no thought tags
        response3 = "Just a normal response without thoughts."
        match3 = re.search(r"<thought>(.*?)</thought>", response3, re.DOTALL)
        assert match3 is None

        print("   ✓ Thought extraction regex works correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_thought_stripping():
    """Test stripping thought tags from responses."""
    print("\n6. Testing thought stripping...")

    try:
        response = "<thought>Internal planning</thought>\nActual user-facing response."

        # Strip thought tags
        cleaned = re.sub(r"<thought>.*?</thought>\s*", "", response, flags=re.DOTALL)

        assert "<thought>" not in cleaned
        assert "</thought>" not in cleaned
        assert cleaned == "Actual user-facing response."

        print("   ✓ Thought tags stripped correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_thought_formatting_inline():
    """Test formatting thoughts for inline display."""
    print("\n7. Testing thought formatting (inline mode)...")

    try:
        response = "<thought>Internal planning</thought>\nActual response."
        thought_content = "Internal planning"

        # Format thought inline
        formatted_thought = f"*💭 [Thought: {thought_content}]*\n\n"
        formatted_response = re.sub(
            r"<thought>.*?</thought>\s*", formatted_thought, response, flags=re.DOTALL
        )

        assert "*💭 [Thought: Internal planning]*" in formatted_response
        assert "Actual response." in formatted_response
        assert "<thought>" not in formatted_response

        print("   ✓ Thought formatted correctly for inline display")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_no_previous_thought():
    """Test behavior when no previous thought exists."""
    print("\n8. Testing no previous thought...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = MetacognitionEngine(db_path=db_path)
        user_id = "test_user_5"
        persona_id = "test_persona_1"

        # Get previous thought without saving any
        retrieved = engine.get_previous_thought(user_id, persona_id)

        assert retrieved is None
        print("   ✓ Returns None when no previous thought exists")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def run_all_tests():
    """Run all metacognition tests."""
    print("=" * 60)
    print("METACOGNITION ENGINE TEST SUITE")
    print("=" * 60)

    tests = [
        test_save_and_retrieve_thought,
        test_per_user_persona_isolation,
        test_most_recent_thought_returned,
        test_clear_thoughts,
        test_thought_extraction_regex,
        test_thought_stripping,
        test_thought_formatting_inline,
        test_no_previous_thought,
    ]

    results = []
    for test in tests:
        results.append(test())

    # Print summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed!")
    else:
        print(f"✗ {total - passed} test(s) failed")

    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
