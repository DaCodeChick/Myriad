#!/usr/bin/env python3
"""
Test script for tool execution (function calling).
This verifies that the tool registry, execution loop, and LLM integration work correctly.
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_registry import ToolRegistry, parse_tool_call, format_tool_response


def test_tool_registry():
    """Test tool registration and retrieval."""
    print("=" * 60)
    print("TOOL REGISTRY TEST")
    print("=" * 60)

    print("\n1. Initializing ToolRegistry...")
    try:
        registry = ToolRegistry()
        print("   ✓ ToolRegistry initialized")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n2. Checking built-in tools...")
    tools = registry.tools  # Access tools dict directly
    print(f"   ✓ Found {len(tools)} registered tools")

    expected_tools = ["get_current_time", "roll_dice"]
    for tool_name in expected_tools:
        if tool_name in tools:
            print(f"   ✓ Tool '{tool_name}' is registered")
        else:
            print(f"   ✗ Tool '{tool_name}' is missing")
            return False

    print("\n3. Verifying tool definitions...")
    definitions = registry.get_tool_definitions()
    print(f"   ✓ Retrieved {len(definitions)} tool definitions")

    for tool_def in definitions:
        name = tool_def.get("name", "UNKNOWN")
        desc = tool_def.get("description", "")
        params = tool_def.get("parameters", {})
        print(f"   - {name}: {desc[:50]}...")
        print(f"     Parameters: {list(params.get('properties', {}).keys())}")

    print("\n4. Testing tool definitions text formatting...")
    tool_text = registry.get_tool_definitions_text()
    if "get_current_time" in tool_text and "roll_dice" in tool_text:
        print("   ✓ Tool definitions formatted correctly")
        print(f"   ✓ Length: {len(tool_text)} characters")
    else:
        print("   ✗ Tool definitions text is incomplete")
        return False

    print("\n" + "=" * 60)
    print("✓ TOOL REGISTRY TEST PASSED")
    print("=" * 60)
    return True


def test_tool_execution():
    """Test actual tool execution."""
    print("\n" + "=" * 60)
    print("TOOL EXECUTION TEST")
    print("=" * 60)

    print("\n1. Initializing ToolRegistry...")
    registry = ToolRegistry()

    print("\n2. Testing get_current_time() execution...")
    try:
        result = registry.execute_tool("get_current_time", {})
        print(f"   ✓ Result: {result}")

        # Verify result contains expected keys
        if result.get("success") and result.get("result"):
            print("   ✓ Result has correct structure")
        else:
            print("   ✗ Result structure is incorrect")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n3. Testing roll_dice() execution...")
    test_cases = [
        {"sides": 6},
        {"sides": 20},
        {"sides": 100},
    ]

    for test_case in test_cases:
        try:
            result = registry.execute_tool("roll_dice", test_case)
            sides = test_case["sides"]
            roll = result.get("result", {}).get("roll")

            if roll and 1 <= roll <= sides:
                print(f"   ✓ roll_dice(sides={sides}) = {roll} (valid range)")
            else:
                print(f"   ✗ roll_dice(sides={sides}) = {roll} (out of range!)")
                return False
        except Exception as e:
            print(f"   ✗ Error with {test_case}: {e}")
            return False

    print("\n4. Testing invalid tool execution...")
    try:
        result = registry.execute_tool("nonexistent_tool", {})
        if "error" in result:
            print(f"   ✓ Invalid tool handled gracefully: {result['error']}")
        else:
            print("   ✗ Invalid tool should return error")
            return False
    except Exception as e:
        print(f"   ✗ Unexpected exception: {e}")
        return False

    print("\n5. Testing tool execution with invalid arguments...")
    try:
        result = registry.execute_tool("roll_dice", {"sides": "not_a_number"})
        if "error" in result:
            print(
                f"   ✓ Invalid arguments handled gracefully: {result['error'][:60]}..."
            )
        else:
            print("   ✗ Invalid arguments should return error")
            return False
    except Exception as e:
        print(f"   ✗ Unexpected exception: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ TOOL EXECUTION TEST PASSED")
    print("=" * 60)
    return True


def test_tool_call_parsing():
    """Test parsing of LLM tool call responses."""
    print("\n" + "=" * 60)
    print("TOOL CALL PARSING TEST")
    print("=" * 60)

    print("\n1. Testing valid JSON tool call...")
    valid_json = '{"tool": "get_current_time", "arguments": {}}'
    result = parse_tool_call(valid_json)
    if (
        result
        and result.get("tool") == "get_current_time"
        and result.get("arguments") == {}
    ):
        print(
            f"   ✓ Parsed correctly: tool={result['tool']}, args={result['arguments']}"
        )
    else:
        print(f"   ✗ Parse failed: {result}")
        return False

    print("\n2. Testing tool call with arguments...")
    with_args = '{"tool": "roll_dice", "arguments": {"sides": 20}}'
    result = parse_tool_call(with_args)
    if (
        result
        and result.get("tool") == "roll_dice"
        and result.get("arguments") == {"sides": 20}
    ):
        print(
            f"   ✓ Parsed correctly: tool={result['tool']}, args={result['arguments']}"
        )
    else:
        print(f"   ✗ Parse failed: {result}")
        return False

    print("\n3. Testing tool call in markdown code block...")
    markdown_json = '```json\n{"tool": "get_current_time", "arguments": {}}\n```'
    result = parse_tool_call(markdown_json)
    if result and result.get("tool") == "get_current_time":
        print(f"   ✓ Parsed markdown JSON correctly: {result['tool']}")
    else:
        print(f"   ✗ Parse failed: {result}")
        return False

    print("\n4. Testing regular text (not a tool call)...")
    regular_text = "The current time is 3:45 PM"
    result = parse_tool_call(regular_text)
    if result is None:
        print("   ✓ Correctly identified as non-tool-call")
    else:
        print(f"   ✗ Should return None for regular text, got: {result}")
        return False

    print("\n5. Testing invalid JSON...")
    invalid_json = '{"tool": "get_time", "incomplete'
    result = parse_tool_call(invalid_json)
    if result is None:
        print("   ✓ Invalid JSON handled gracefully")
    else:
        print(f"   ✗ Should return None for invalid JSON, got: {result}")
        return False

    print("\n6. Testing JSON without required fields...")
    no_tool_field = '{"function": "get_time", "arguments": {}}'
    result = parse_tool_call(no_tool_field)
    if result is None:
        print("   ✓ Missing 'tool' field handled correctly")
    else:
        print(f"   ✗ Should return None without 'tool' field, got: {result}")
        return False

    print("\n" + "=" * 60)
    print("✓ TOOL CALL PARSING TEST PASSED")
    print("=" * 60)
    return True


def test_tool_response_formatting():
    """Test formatting of tool execution results."""
    print("\n" + "=" * 60)
    print("TOOL RESPONSE FORMATTING TEST")
    print("=" * 60)

    print("\n1. Testing successful tool response formatting...")
    result = {
        "success": True,
        "result": {"current_time": "2026-03-13 10:30:45", "timezone": "UTC"},
        "error": None,
    }
    formatted = format_tool_response("get_current_time", result)

    if "get_current_time" in formatted and "current_time" in formatted:
        print(f"   ✓ Formatted correctly")
        print(f"   Response preview: {formatted[:100]}...")
    else:
        print(f"   ✗ Formatting failed: {formatted}")
        return False

    print("\n2. Testing error response formatting...")
    error_result = {"success": False, "error": "Something went wrong", "result": None}
    formatted = format_tool_response("roll_dice", error_result)

    if "error" in formatted.lower():
        print(f"   ✓ Error formatted correctly")
        print(f"   Response preview: {formatted[:100]}...")
    else:
        print(f"   ✗ Error formatting failed: {formatted}")
        return False

    print("\n" + "=" * 60)
    print("✓ TOOL RESPONSE FORMATTING TEST PASSED")
    print("=" * 60)
    return True


def run_all_tests():
    """Run all tool execution tests."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "TOOL EXECUTION TEST SUITE" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    tests = [
        ("Tool Registry", test_tool_registry),
        ("Tool Execution", test_tool_execution),
        ("Tool Call Parsing", test_tool_call_parsing),
        ("Tool Response Formatting", test_tool_response_formatting),
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
