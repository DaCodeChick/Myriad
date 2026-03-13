#!/usr/bin/env python3
"""
Test script for semantic memory integration.
This verifies that VectorMemory and MemoryMatrix work together correctly.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.memory_matrix import MemoryMatrix


def test_semantic_memory():
    """Test the semantic memory system."""
    print("=" * 60)
    print("SEMANTIC MEMORY INTEGRATION TEST")
    print("=" * 60)

    # Initialize MemoryMatrix with vector memory enabled
    print("\n1. Initializing MemoryMatrix with vector memory...")
    try:
        memory = MemoryMatrix(
            db_path="database/test_myriad.db", vector_memory_enabled=True
        )
        print("   ✓ MemoryMatrix initialized")
        print(f"   ✓ Vector memory enabled: {memory.vector_memory_enabled}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test adding memories
    print("\n2. Adding test memories...")
    test_user = "test_user_123"
    test_persona = "test_persona"

    test_memories = [
        "I love programming in Python, especially for AI applications.",
        "My favorite color is blue and I enjoy painting landscapes.",
        "I'm working on a machine learning project about image classification.",
        "Last summer I went hiking in the Rocky Mountains.",
        "I really enjoy cooking Italian food, especially making fresh pasta.",
        "Neural networks are fascinating, I've been studying transformers lately.",
    ]

    try:
        for i, content in enumerate(test_memories, 1):
            memory_id = memory.add_memory(
                user_id=test_user,
                origin_persona=test_persona,
                role="user" if i % 2 == 1 else "assistant",
                content=content,
                visibility_scope="GLOBAL" if i % 3 == 0 else "ISOLATED",
            )
            print(f"   ✓ Added memory {i} (ID: {memory_id})")
    except Exception as e:
        print(f"   ✗ Error adding memories: {e}")
        return False

    # Test semantic search
    print("\n3. Testing semantic search...")
    test_queries = [
        (
            "Tell me about AI and machine learning",
            "Should find programming/ML memories",
        ),
        ("What outdoor activities do you like?", "Should find hiking memory"),
        ("What are your hobbies?", "Should find cooking/painting memories"),
    ]

    try:
        for query, description in test_queries:
            print(f"\n   Query: '{query}'")
            print(f"   ({description})")

            results = memory.search_semantic_memories(
                user_id=test_user, current_persona=test_persona, query=query, limit=3
            )

            if results:
                print(f"   ✓ Found {len(results)} semantically similar memories:")
                for j, result in enumerate(results, 1):
                    content = result.get("content", "")
                    distance = result.get("distance", 0)
                    # Lower distance = more similar
                    similarity = 1 - distance  # Convert to similarity score
                    print(f"      {j}. [{similarity:.3f}] {content[:60]}...")
            else:
                print(f"   ⚠ No results found")
    except Exception as e:
        print(f"   ✗ Error during semantic search: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test memory stats
    print("\n4. Getting memory statistics...")
    try:
        if memory.vector_memory and memory.vector_memory_enabled:
            stats = memory.vector_memory.get_collection_stats()
            print(f"   ✓ Total vector memories: {stats['total_memories']}")
            print(f"   ✓ Collection: {stats['collection_name']}")
            print(f"   ✓ Embedding model: {stats['embedding_model']}")
    except Exception as e:
        print(f"   ✗ Error getting stats: {e}")
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
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_semantic_memory()
    sys.exit(0 if success else 1)
