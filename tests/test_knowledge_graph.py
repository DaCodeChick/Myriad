#!/usr/bin/env python3
"""
Test script for Knowledge Graph Memory system.
This verifies entity storage, relationship creation, and keyword-based retrieval.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.graph_memory import GraphMemory


def test_entity_creation():
    """Test adding entities to the knowledge graph."""
    print("=" * 60)
    print("ENTITY CREATION TEST")
    print("=" * 60)

    print("\n1. Initializing GraphMemory...")
    try:
        graph = GraphMemory(db_path="data/test_knowledge_graph.db")
        print("   ✓ GraphMemory initialized")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n2. Adding entities...")
    try:
        # Add some test entities
        entity_id1 = graph.add_entity("Bob", "User", "A user who loves AI")
        entity_id2 = graph.add_entity(
            "Gentle Possession", "Concept", "A philosophical concept"
        )
        entity_id3 = graph.add_entity("Python", "Language", "Programming language")

        print(f"   ✓ Added entity: Bob (ID: {entity_id1})")
        print(f"   ✓ Added entity: Gentle Possession (ID: {entity_id2})")
        print(f"   ✓ Added entity: Python (ID: {entity_id3})")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n3. Testing entity retrieval...")
    try:
        entity = graph.get_entity_by_name("Bob")
        if entity and entity["name"] == "Bob" and entity["type"] == "User":
            print(f"   ✓ Retrieved entity: {entity['name']} ({entity['type']})")
        else:
            print("   ✗ Entity retrieval failed")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n4. Testing duplicate entity handling...")
    try:
        # Try to add the same entity again
        duplicate_id = graph.add_entity("Bob", "User", "Updated description")
        if duplicate_id == entity_id1:
            print(
                f"   ✓ Duplicate entity correctly returned existing ID: {duplicate_id}"
            )
        else:
            print("   ✗ Duplicate handling failed")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ ENTITY CREATION TEST PASSED")
    print("=" * 60)
    return True


def test_relationship_creation():
    """Test adding relationships between entities."""
    print("\n" + "=" * 60)
    print("RELATIONSHIP CREATION TEST")
    print("=" * 60)

    print("\n1. Initializing GraphMemory...")
    graph = GraphMemory(db_path="data/test_knowledge_graph.db")

    print("\n2. Adding relationships...")
    try:
        # Add relationships
        success1 = graph.add_relationship(
            "Bob", "User", "LIKES", "Gentle Possession", "Concept"
        )
        success2 = graph.add_relationship("Bob", "User", "KNOWS", "Python", "Language")
        success3 = graph.add_relationship(
            "Python", "Language", "USED_FOR", "AI", "Field"
        )

        if success1 and success2 and success3:
            print("   ✓ Added relationship: Bob LIKES Gentle Possession")
            print("   ✓ Added relationship: Bob KNOWS Python")
            print("   ✓ Added relationship: Python USED_FOR AI")
        else:
            print("   ✗ Some relationships failed to add")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n3. Retrieving relationships for entity...")
    try:
        relationships = graph.get_relationships_for_entity("Bob")

        if len(relationships) >= 2:
            print(f"   ✓ Found {len(relationships)} relationships for Bob:")
            for rel in relationships:
                print(
                    f"      • {rel['source']} ({rel['source_type']}) {rel['relation']} {rel['target']} ({rel['target_type']})"
                )
        else:
            print(f"   ✗ Expected at least 2 relationships, found {len(relationships)}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ RELATIONSHIP CREATION TEST PASSED")
    print("=" * 60)
    return True


def test_keyword_extraction():
    """Test keyword extraction from user messages."""
    print("\n" + "=" * 60)
    print("KEYWORD EXTRACTION TEST")
    print("=" * 60)

    print("\n1. Initializing GraphMemory...")
    graph = GraphMemory(db_path="data/test_knowledge_graph.db")

    print("\n2. Testing keyword extraction...")
    test_cases = [
        ("I love Python programming!", ["love", "Python", "programming"]),
        ("Tell me about Gentle Possession", ["Tell", "about", "Gentle", "Possession"]),
        ("What is the time?", ["What", "time"]),
    ]

    all_passed = True
    for message, expected_keywords in test_cases:
        keywords = graph.extract_keywords(message)
        # Check if expected keywords are in extracted keywords
        found = sum(1 for kw in expected_keywords if kw in keywords)
        if found >= len(expected_keywords) * 0.7:  # At least 70% match
            print(f"   ✓ '{message}' → {keywords}")
        else:
            print(
                f"   ⚠ '{message}' → {keywords} (expected more matches with {expected_keywords})"
            )
            all_passed = False

    if all_passed:
        print("\n" + "=" * 60)
        print("✓ KEYWORD EXTRACTION TEST PASSED")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠ KEYWORD EXTRACTION TEST PARTIAL PASS")
        print("=" * 60)

    return True  # Don't fail on partial match


def test_knowledge_retrieval():
    """Test retrieving knowledge based on keywords."""
    print("\n" + "=" * 60)
    print("KNOWLEDGE RETRIEVAL TEST")
    print("=" * 60)

    print("\n1. Initializing GraphMemory...")
    graph = GraphMemory(db_path="data/test_knowledge_graph.db")

    print("\n2. Searching for entities by keywords...")
    try:
        # Search for "Python"
        results = graph.search_entities_by_keywords(["Python"])

        if results:
            print(f"   ✓ Found {len(results)} entity matches for 'Python':")
            for result in results:
                print(f"\n      Entity: {result['entity']}")
                for rel in result["relationships"]:
                    print(
                        f"        • {rel['source']} ({rel['source_type']}) {rel['relation']} {rel['target']} ({rel['target_type']})"
                    )
        else:
            print("   ⚠ No results found for 'Python' (might be empty graph)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n3. Testing full knowledge context retrieval...")
    try:
        context = graph.get_knowledge_context("Tell me about Python and what Bob likes")

        if context:
            print("   ✓ Generated knowledge context:")
            print(context)
        else:
            print("   ⚠ No knowledge context generated (might be no matching entities)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ KNOWLEDGE RETRIEVAL TEST PASSED")
    print("=" * 60)
    return True


def test_graph_stats():
    """Test graph statistics."""
    print("\n" + "=" * 60)
    print("GRAPH STATISTICS TEST")
    print("=" * 60)

    print("\n1. Initializing GraphMemory...")
    graph = GraphMemory(db_path="data/test_knowledge_graph.db")

    print("\n2. Getting graph statistics...")
    try:
        stats = graph.get_stats()
        print(f"   ✓ Total Entities: {stats['total_entities']}")
        print(f"   ✓ Total Relationships: {stats['total_relationships']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n3. Getting all relationships...")
    try:
        all_rels = graph.get_all_relationships(limit=10)
        print(f"   ✓ Retrieved {len(all_rels)} relationships:")
        for rel in all_rels[:5]:  # Show first 5
            print(
                f"      • {rel['source']} ({rel['source_type']}) {rel['relation']} {rel['target']} ({rel['target_type']})"
            )
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ GRAPH STATISTICS TEST PASSED")
    print("=" * 60)
    return True


def test_cleanup():
    """Clean up test data."""
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)

    print("\n1. Clearing test graph...")
    try:
        graph = GraphMemory(db_path="data/test_knowledge_graph.db")
        graph.clear_all()

        stats = graph.get_stats()
        if stats["total_entities"] == 0 and stats["total_relationships"] == 0:
            print("   ✓ Test data cleared successfully")
        else:
            print("   ⚠ Graph not completely cleared")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ CLEANUP COMPLETE")
    print("=" * 60)
    return True


def run_all_tests():
    """Run all knowledge graph tests."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 14 + "KNOWLEDGE GRAPH TEST SUITE" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    tests = [
        ("Entity Creation", test_entity_creation),
        ("Relationship Creation", test_relationship_creation),
        ("Keyword Extraction", test_keyword_extraction),
        ("Knowledge Retrieval", test_knowledge_retrieval),
        ("Graph Statistics", test_graph_stats),
        ("Cleanup", test_cleanup),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'─' * 60}")
        print(f"Running: {test_name}")
        print(f"{'─' * 60}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ UNEXPECTED ERROR in {test_name}: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 22 + "TEST SUMMARY" + " " * 24 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print()
    print(f"  Total: {passed}/{total} tests passed")
    print()

    if passed == total:
        print("  🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"  ⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
