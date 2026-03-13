#!/usr/bin/env python3
"""
Test script for the Digital Pharmacy (Substance-Based Limbic Overrides).

This test suite validates:
1. Substance consumption and state overrides
2. Unclamped state-setting (values > 1.0)
3. Prompt modifier injection
4. Active substance tracking
5. Substance clearing
"""

import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.limbic_engine import LimbicEngine
from database.limbic_modifiers import DigitalPharmacy


def test_consume_substance_xanax():
    """Test consuming Xanax sets GABA=1.5 and CORTISOL=0.0."""
    print("\n1. Testing Xanax consumption...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_1"
        persona_id = "test_persona_1"

        # Consume Xanax
        result = pharmacy.consume_substance(user_id, persona_id, "xanax")
        state = engine.get_state(user_id, persona_id)

        assert state["GABA"] == 1.5, f"Expected GABA=1.5, got {state['GABA']}"
        assert state["CORTISOL"] == 0.0, (
            f"Expected CORTISOL=0.0, got {state['CORTISOL']}"
        )
        assert "xanax" in result.lower()
        print("   ✓ Xanax set GABA=1.5, CORTISOL=0.0 (unclamped)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_consume_substance_mdma():
    """Test consuming MDMA sets OXYTOCIN=1.5, DOPAMINE=1.0, CORTISOL=0.0."""
    print("\n2. Testing MDMA consumption...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_2"
        persona_id = "test_persona_1"

        # Consume MDMA
        result = pharmacy.consume_substance(user_id, persona_id, "mdma")
        state = engine.get_state(user_id, persona_id)

        assert state["OXYTOCIN"] == 1.5, (
            f"Expected OXYTOCIN=1.5, got {state['OXYTOCIN']}"
        )
        assert state["DOPAMINE"] == 1.0, (
            f"Expected DOPAMINE=1.0, got {state['DOPAMINE']}"
        )
        assert state["CORTISOL"] == 0.0, (
            f"Expected CORTISOL=0.0, got {state['CORTISOL']}"
        )
        assert "mdma" in result.lower()
        print("   ✓ MDMA set OXYTOCIN=1.5, DOPAMINE=1.0, CORTISOL=0.0")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_consume_substance_fear_toxin():
    """Test consuming Fear Toxin sets CORTISOL=1.5, GABA=0.0."""
    print("\n3. Testing Fear Toxin consumption...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_3"
        persona_id = "test_persona_1"

        # Consume Fear Toxin
        result = pharmacy.consume_substance(user_id, persona_id, "fear_toxin")
        state = engine.get_state(user_id, persona_id)

        assert state["CORTISOL"] == 1.5, (
            f"Expected CORTISOL=1.5, got {state['CORTISOL']}"
        )
        assert state["GABA"] == 0.0, f"Expected GABA=0.0, got {state['GABA']}"
        assert "fear_toxin" in result.lower() or "fear toxin" in result.lower()
        print("   ✓ Fear Toxin set CORTISOL=1.5, GABA=0.0")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_active_substance_tracking():
    """Test that active substance is tracked per user/persona."""
    print("\n4. Testing active substance tracking...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_4"
        persona_id = "test_persona_1"

        # No active substance initially
        active = pharmacy.get_active_substance(user_id, persona_id)
        assert active is None, f"Expected no active substance, got {active}"

        # Consume cocaine
        pharmacy.consume_substance(user_id, persona_id, "cocaine")
        active = pharmacy.get_active_substance(user_id, persona_id)
        assert active == "cocaine", f"Expected cocaine, got {active}"

        print("   ✓ Active substance tracked correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_substance_prompt_modifier():
    """Test that substance prompt modifier is returned correctly."""
    print("\n5. Testing substance prompt modifier...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_5"
        persona_id = "test_persona_1"

        # No modifier initially
        modifier = pharmacy.get_substance_prompt_modifier(user_id, persona_id)
        assert modifier is None, f"Expected no modifier, got {modifier}"

        # Consume LSD
        pharmacy.consume_substance(user_id, persona_id, "lsd")
        modifier = pharmacy.get_substance_prompt_modifier(user_id, persona_id)
        assert modifier is not None, "Expected modifier after LSD consumption"
        assert len(modifier) > 0, "Expected non-empty modifier"

        print("   ✓ Substance prompt modifier injected correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_clear_substance():
    """Test clearing active substance."""
    print("\n6. Testing substance clearing...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_6"
        persona_id = "test_persona_1"

        # Consume morphine
        pharmacy.consume_substance(user_id, persona_id, "morphine")
        active = pharmacy.get_active_substance(user_id, persona_id)
        assert active == "morphine", f"Expected morphine, got {active}"

        # Clear substance
        pharmacy.clear_substance(user_id, persona_id)
        active = pharmacy.get_active_substance(user_id, persona_id)
        assert active is None, f"Expected no active substance after clear, got {active}"

        print("   ✓ Substance cleared correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_invalid_substance():
    """Test consuming invalid substance returns error."""
    print("\n7. Testing invalid substance handling...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_7"
        persona_id = "test_persona_1"

        # Try to consume invalid substance
        result = pharmacy.consume_substance(user_id, persona_id, "invalid_substance")
        assert "error" in result.lower() or "unknown" in result.lower()

        print("   ✓ Invalid substance handled correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_unclamped_values_bypass_normal_limits():
    """Test that unclamped values bypass the normal 0.0-1.0 limits."""
    print("\n8. Testing unclamped state-setting bypasses limits...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = LimbicEngine(db_path=db_path)
        pharmacy = DigitalPharmacy(engine)
        user_id = "test_user_8"
        persona_id = "test_persona_1"

        # Manually set unclamped value
        pharmacy._set_state_unclamped(user_id, persona_id, "DOPAMINE", 2.5)
        state = engine.get_state(user_id, persona_id)

        assert state["DOPAMINE"] == 2.5, (
            f"Expected DOPAMINE=2.5, got {state['DOPAMINE']}"
        )
        print("   ✓ Unclamped values bypass 0.0-1.0 limits (DOPAMINE=2.5)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def run_all_tests():
    """Run all Digital Pharmacy tests."""
    print("\n" + "=" * 60)
    print("DIGITAL PHARMACY TEST SUITE")
    print("=" * 60)

    tests = [
        test_consume_substance_xanax,
        test_consume_substance_mdma,
        test_consume_substance_fear_toxin,
        test_active_substance_tracking,
        test_substance_prompt_modifier,
        test_clear_substance,
        test_invalid_substance,
        test_unclamped_values_bypass_normal_limits,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ✗ Test crashed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed > 0:
        print(f"         {failed} tests failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
