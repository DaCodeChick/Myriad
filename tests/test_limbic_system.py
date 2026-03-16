#!/usr/bin/env python3
"""
Test script for the Limbic System (Emotional Neurochemistry).

This test suite validates:
1. Emotional state initialization (baseline 0.5)
2. inject_emotion with various deltas
3. Value clamping (0.0 to 1.0)
4. Metabolic decay (10% toward baseline)
5. Limbic context formatting
6. State persistence across turns
"""

import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.features.roleplay.limbic_engine import LimbicEngine


def test_initial_state_is_baseline():
    """Test that initial emotional state is baseline (0.5) for all chemicals."""
    print("\n1. Testing initial state is baseline...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_1"
        persona_id = "test_persona_1"

        state = engine.get_state(user_id, persona_id)

        assert state["DOPAMINE"] == 0.5
        assert state["CORTISOL"] == 0.5
        assert state["OXYTOCIN"] == 0.5
        assert state["GABA"] == 0.5
        print("   ✓ All chemicals initialized to baseline (0.5)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_inject_emotion_positive_delta():
    """Test injecting emotion with positive delta increases chemical level."""
    print("\n2. Testing positive delta injection...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_2"
        persona_id = "test_persona_1"

        # Inject DOPAMINE +0.2
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.2)
        state = engine.get_state(user_id, persona_id)

        assert state["DOPAMINE"] == 0.7  # 0.5 + 0.2 = 0.7
        assert state["CORTISOL"] == 0.5  # Other chemicals unchanged
        print("   ✓ DOPAMINE increased from 0.5 to 0.7 (delta +0.2)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_inject_emotion_negative_delta():
    """Test injecting emotion with negative delta decreases chemical level."""
    print("\n3. Testing negative delta injection...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_3"
        persona_id = "test_persona_1"

        # Inject CORTISOL -0.15
        engine.inject_emotion(user_id, persona_id, "CORTISOL", -0.15)
        state = engine.get_state(user_id, persona_id)

        assert state["CORTISOL"] == 0.35  # 0.5 - 0.15 = 0.35
        assert state["DOPAMINE"] == 0.5  # Other chemicals unchanged
        print("   ✓ CORTISOL decreased from 0.5 to 0.35 (delta -0.15)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_value_clamping_upper_bound():
    """Test that chemical values are clamped to maximum of 1.0."""
    print("\n4. Testing upper bound clamping (1.0)...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_4"
        persona_id = "test_persona_1"

        # Inject OXYTOCIN +0.3 twice (should clamp at 1.0)
        engine.inject_emotion(user_id, persona_id, "OXYTOCIN", 0.3)  # 0.5 + 0.3 = 0.8
        engine.inject_emotion(user_id, persona_id, "OXYTOCIN", 0.3)  # 0.8 + 0.3 = 1.1 -> clamped
        state = engine.get_state(user_id, persona_id)

        assert state["OXYTOCIN"] == 1.0  # Clamped at maximum
        print("   ✓ OXYTOCIN clamped at 1.0 (attempted 1.1)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_value_clamping_lower_bound():
    """Test that chemical values are clamped to minimum of 0.0."""
    print("\n5. Testing lower bound clamping (0.0)...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_5"
        persona_id = "test_persona_1"

        # Inject GABA -0.3 twice (should clamp at 0.0)
        engine.inject_emotion(user_id, persona_id, "GABA", -0.3)  # 0.5 - 0.3 = 0.2
        engine.inject_emotion(user_id, persona_id, "GABA", -0.3)  # 0.2 - 0.3 = -0.1 -> clamped
        state = engine.get_state(user_id, persona_id)

        assert state["GABA"] == 0.0  # Clamped at minimum
        print("   ✓ GABA clamped at 0.0 (attempted -0.1)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_metabolic_decay_toward_baseline():
    """Test that metabolic decay pulls values toward baseline (0.5) by 10%."""
    print("\n6. Testing metabolic decay (10% toward baseline)...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_6"
        persona_id = "test_persona_1"

        # Set DOPAMINE to 1.0 (max) using multiple injections
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.3)  # -> 0.8
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.2)  # -> 1.0

        # Apply decay
        new_state = engine.apply_metabolic_decay(user_id, persona_id)

        # Expected: 1.0 + (0.5 - 1.0) * 0.1 = 1.0 - 0.05 = 0.95
        assert abs(new_state["DOPAMINE"] - 0.95) < 0.001
        print("   ✓ DOPAMINE decayed from 1.0 to 0.95 (10% toward baseline 0.5)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_metabolic_decay_multiple_chemicals():
    """Test that metabolic decay affects all chemicals simultaneously."""
    print("\n7. Testing metabolic decay on multiple chemicals...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_7"
        persona_id = "test_persona_1"

        # Set different values for different chemicals
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.3)  # -> 0.8
        engine.inject_emotion(user_id, persona_id, "CORTISOL", -0.2)  # -> 0.3
        # Split OXYTOCIN injection into valid deltas
        engine.inject_emotion(user_id, persona_id, "OXYTOCIN", 0.3)  # -> 0.8
        engine.inject_emotion(user_id, persona_id, "OXYTOCIN", 0.1)  # -> 0.9

        # Apply decay
        new_state = engine.apply_metabolic_decay(user_id, persona_id)

        # Verify all chemicals decayed toward baseline
        assert abs(new_state["DOPAMINE"] - 0.77) < 0.001  # 0.8 -> 0.77
        assert abs(new_state["CORTISOL"] - 0.32) < 0.001  # 0.3 -> 0.32
        assert abs(new_state["OXYTOCIN"] - 0.86) < 0.001  # 0.9 -> 0.86
        print("   ✓ All chemicals decayed simultaneously toward baseline")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_limbic_context_formatting():
    """Test that limbic context is formatted correctly for system prompt injection."""
    print("\n8. Testing limbic context formatting...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_8"
        persona_id = "test_persona_1"

        # Set distinctive chemical levels
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.3)  # -> 0.8
        engine.inject_emotion(user_id, persona_id, "CORTISOL", -0.3)  # -> 0.2

        context = engine.get_limbic_context(user_id, persona_id)

        # Should contain all chemicals
        assert "DOPAMINE" in context
        assert "CORTISOL" in context
        assert "OXYTOCIN" in context
        assert "GABA" in context
        print("   ✓ Limbic context contains all chemicals")
        print(f"   Context sample: {context[:100]}...")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_state_persistence_across_turns():
    """Test that emotional state persists across multiple turns."""
    print("\n9. Testing state persistence...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_9"
        persona_id = "test_persona_1"

        # Turn 1: Inject emotion
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.2)

        # Turn 2: Retrieve state (should persist)
        state = engine.get_state(user_id, persona_id)
        assert state["DOPAMINE"] == 0.7

        # Turn 3: Apply decay
        engine.apply_metabolic_decay(user_id, persona_id)

        # Turn 4: Retrieve state again
        state = engine.get_state(user_id, persona_id)
        assert abs(state["DOPAMINE"] - 0.68) < 0.001
        print("   ✓ State persisted correctly across 4 turns")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_isolated_states_per_user_persona():
    """Test that different user/persona combinations have isolated states."""
    print("\n10. Testing state isolation per user/persona...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user1 = "user_alice"
        user2 = "user_bob"
        persona1 = "persona_dominant"
        persona2 = "persona_submissive"

        # User1 + Persona1
        engine.inject_emotion(user1, persona1, "DOPAMINE", 0.3)

        # User1 + Persona2
        engine.inject_emotion(user1, persona2, "OXYTOCIN", 0.3)

        # User2 + Persona1
        engine.inject_emotion(user2, persona1, "CORTISOL", 0.2)

        # Check isolation
        state1_1 = engine.get_state(user1, persona1)
        state1_2 = engine.get_state(user1, persona2)
        state2_1 = engine.get_state(user2, persona1)

        assert state1_1["DOPAMINE"] == 0.8
        assert state1_1["OXYTOCIN"] == 0.5  # Baseline
        assert state1_2["OXYTOCIN"] == 0.8
        assert state1_2["DOPAMINE"] == 0.5  # Baseline
        assert state2_1["CORTISOL"] == 0.7
        print("   ✓ States correctly isolated per user/persona combination")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_reset_state():
    """Test that reset_state returns all chemicals to baseline."""
    print("\n11. Testing state reset...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_10"
        persona_id = "test_persona_1"

        # Set extreme values (split into valid deltas)
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.3)  # -> 0.8
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.2)  # -> 1.0
        engine.inject_emotion(user_id, persona_id, "CORTISOL", -0.3)  # -> 0.2
        engine.inject_emotion(user_id, persona_id, "CORTISOL", -0.2)  # -> 0.0

        # Reset
        engine.reset_state(user_id, persona_id)

        # Check all back to baseline
        state = engine.get_state(user_id, persona_id)
        assert state["DOPAMINE"] == 0.5
        assert state["CORTISOL"] == 0.5
        assert state["OXYTOCIN"] == 0.5
        assert state["GABA"] == 0.5
        print("   ✓ All chemicals reset to baseline (0.5)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_extreme_decay_converges_to_baseline():
    """Test that repeated decay eventually converges to baseline."""
    print("\n12. Testing decay convergence to baseline...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        engine = LimbicEngine(db_path=db_path)
        user_id = "test_user_12"
        persona_id = "test_persona_1"

        # Set to extreme (split into valid deltas)
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.3)  # -> 0.8
        engine.inject_emotion(user_id, persona_id, "DOPAMINE", 0.2)  # -> 1.0

        # Apply decay 50 times
        for _ in range(50):
            engine.apply_metabolic_decay(user_id, persona_id)

        state = engine.get_state(user_id, persona_id)

        # Should be very close to baseline (within 0.01)
        assert abs(state["DOPAMINE"] - 0.5) < 0.01
        print(f"   ✓ DOPAMINE converged from 1.0 to {state['DOPAMINE']:.4f} after 50 decays")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    """Run all limbic system tests."""
    print("=" * 60)
    print("LIMBIC SYSTEM (EMOTIONAL NEUROCHEMISTRY) TEST SUITE")
    print("=" * 60)

    tests = [
        test_initial_state_is_baseline,
        test_inject_emotion_positive_delta,
        test_inject_emotion_negative_delta,
        test_value_clamping_upper_bound,
        test_value_clamping_lower_bound,
        test_metabolic_decay_toward_baseline,
        test_metabolic_decay_multiple_chemicals,
        test_limbic_context_formatting,
        test_state_persistence_across_turns,
        test_isolated_states_per_user_persona,
        test_reset_state,
        test_extreme_decay_converges_to_baseline,
    ]

    results = []
    for test in tests:
        results.append(test())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"✗ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
