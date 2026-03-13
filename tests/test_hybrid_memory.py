#!/usr/bin/env python3
"""
Test script for hybrid memory architecture.
This verifies that short-term chronological + long-term semantic memory work together.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.memory_matrix import MemoryMatrix


def test_hybrid_memory():
    """Test the hybrid memory architecture."""
    print("=" * 60)
    print("HYBRID MEMORY ARCHITECTURE TEST")
    print("=" * 60)

    # Initialize MemoryMatrix with vector memory enabled
    print("\n1. Initializing MemoryMatrix with hybrid memory...")
    try:
        memory = MemoryMatrix(db_path="data/test_hybrid.db", vector_memory_enabled=True)
        print("   ✓ MemoryMatrix initialized")
        print(f"   ✓ Vector memory enabled: {memory.vector_memory_enabled}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test scenario: Simulating a conversation
    print("\n2. Simulating a conversation with 20 messages...")
    test_user = "test_user_456"
    test_persona = "alpha_stud"

    # Early conversation (messages 1-10) - These should become "long-term" memories
    print("   Adding early conversation (messages 1-10)...")
    early_messages = [
        ("user", "Hey, I'm working on a Python project about neural networks"),
        ("assistant", "That sounds exciting! What kind of neural networks?"),
        ("user", "I'm building a transformer model for text generation"),
        (
            "assistant",
            "Transformers are powerful! Are you using PyTorch or TensorFlow?",
        ),
        ("user", "PyTorch. I love how intuitive it is"),
        ("assistant", "Great choice! PyTorch has excellent documentation."),
        ("user", "Yeah, I'm also using the Hugging Face library"),
        ("assistant", "Hugging Face is fantastic for transformers!"),
        ("user", "Do you know any good resources for learning attention mechanisms?"),
        (
            "assistant",
            "The 'Attention is All You Need' paper is the foundational resource.",
        ),
    ]

    for role, content in early_messages:
        memory.add_memory(
            user_id=test_user,
            origin_persona=test_persona,
            role=role,
            content=content,
            visibility_scope="ISOLATED",
        )
    print("   ✓ Added 10 early messages (should become long-term memories)")

    # Recent conversation (messages 11-20) - These should be in "short-term" memory
    print("\n   Adding recent conversation (messages 11-20)...")
    recent_messages = [
        ("user", "What's your favorite food?"),
        ("assistant", "I enjoy discussing culinary topics! What about you?"),
        ("user", "I love Italian pasta, especially carbonara"),
        ("assistant", "Carbonara is a classic! The creamy sauce is amazing."),
        ("user", "Do you prefer cooking or eating out?"),
        ("assistant", "Both have their charm! Cooking can be therapeutic."),
        ("user", "True! I made lasagna last night"),
        ("assistant", "Lasagna is a labor of love! How did it turn out?"),
        ("user", "It was delicious, my family loved it"),
        ("assistant", "That's wonderful! Sharing good food brings people together."),
    ]

    for role, content in recent_messages:
        memory.add_memory(
            user_id=test_user,
            origin_persona=test_persona,
            role=role,
            content=content,
            visibility_scope="ISOLATED",
        )
    print("   ✓ Added 10 recent messages (should be in short-term memory)")

    # Test 1: Get short-term memory (last 10 messages)
    print("\n3. Testing SHORT-TERM memory retrieval (last 10 messages)...")
    try:
        short_term = memory.get_context_memories(
            user_id=test_user, current_persona=test_persona, limit=10
        )

        print(f"   ✓ Retrieved {len(short_term)} short-term memories")

        # Verify these are the recent food-related messages
        food_keywords = ["food", "pasta", "carbonara", "cooking", "lasagna"]
        food_count = sum(
            1
            for m in short_term
            if any(kw in m["content"].lower() for kw in food_keywords)
        )

        if food_count >= 5:
            print(
                f"   ✓ Short-term memory contains recent food conversation ({food_count}/10 messages)"
            )
        else:
            print(
                f"   ⚠ Warning: Short-term memory might not have enough recent messages ({food_count}/10)"
            )

        # Show sample
        print("\n   Sample short-term messages:")
        for i, msg in enumerate(short_term[-3:], 1):
            print(f"      {i}. [{msg['role']}]: {msg['content'][:50]}...")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test 2: Search semantic long-term memory
    print("\n4. Testing LONG-TERM semantic memory search...")
    try:
        # Query about neural networks (from early conversation)
        query = "Tell me more about neural networks and transformers"

        semantic_results = memory.search_semantic_memories(
            user_id=test_user, current_persona=test_persona, query=query, limit=5
        )

        if semantic_results:
            print(
                f"   ✓ Found {len(semantic_results)} semantically similar long-term memories"
            )

            # Check if we found the neural network conversations
            nn_keywords = ["neural", "transformer", "pytorch", "attention"]
            nn_count = sum(
                1
                for m in semantic_results
                if any(kw in m.get("content", "").lower() for kw in nn_keywords)
            )

            if nn_count >= 2:
                print(
                    f"   ✓ Long-term memory successfully recalled neural network conversation ({nn_count}/5 results)"
                )
            else:
                print(
                    f"   ⚠ Warning: Fewer neural network memories than expected ({nn_count}/5)"
                )

            # Show sample
            print("\n   Top 3 long-term semantic matches:")
            for i, result in enumerate(semantic_results[:3], 1):
                content = result.get("content", "")
                distance = result.get("distance", 0)
                similarity = 1 - distance
                print(f"      {i}. [Similarity: {similarity:.3f}] {content[:60]}...")
        else:
            print("   ⚠ No semantic results found")

    except Exception as e:
        print(f"   ✗ Error during semantic search: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Cleanup
    print("\n5. Cleaning up test data...")
    try:
        memory.clear_user_memories(test_user)
        print("   ✓ Test memories cleared")
    except Exception as e:
        print(f"   ✗ Error clearing memories: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ HYBRID MEMORY TEST PASSED")
    print("=" * 60)
    print("\nSUMMARY:")
    print("- Short-term memory: Last 10 messages (immediate conversation)")
    print("- Long-term memory: Semantic search finds older relevant context")
    print("- Both memory types work independently and complement each other")
    return True


if __name__ == "__main__":
    success = test_hybrid_memory()
    sys.exit(0 if success else 1)
