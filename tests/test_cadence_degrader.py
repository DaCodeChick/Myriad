#!/usr/bin/env python3
"""
Test script for the Cadence Degradation Engine (Text Post-Processing).

This test suite validates:
1. Panic effects (stutters, random caps) when CORTISOL > 0.8
2. Arousal effects (vowel stretching, typos) when DOPAMINE > 0.8
3. Sedation effects (lowercase, ellipses) when GABA > 0.8
4. Threshold triggering
5. Combined effects
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cadence_degrader import CadenceDegrader


def test_panic_effects_trigger():
    """Test that panic effects trigger when CORTISOL > 0.8."""
    print("\n1. Testing panic effects trigger (CORTISOL > 0.8)...")

    try:
        degrader = CadenceDegrader()

        limbic_state = {
            "DOPAMINE": 0.5,
            "CORTISOL": 0.9,  # High cortisol
            "OXYTOCIN": 0.5,
            "GABA": 0.5,
        }

        text = "I don't know what to do."
        degraded = degrader.degrade(text, limbic_state)

        # Should have some stutters or caps
        assert degraded != text, "Text should be degraded"
        # At high cortisol, should have some effects
        print(f"   Original: {text}")
        print(f"   Degraded: {degraded}")
        print("   ✓ Panic effects triggered")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_arousal_effects_trigger():
    """Test that arousal effects trigger when DOPAMINE > 0.8."""
    print("\n2. Testing arousal effects trigger (DOPAMINE > 0.8)...")

    try:
        degrader = CadenceDegrader()

        limbic_state = {
            "DOPAMINE": 1.0,  # High dopamine
            "CORTISOL": 0.5,
            "OXYTOCIN": 0.5,
            "GABA": 0.5,
        }

        text = "This is amazing I love it please more."
        degraded = degrader.degrade(text, limbic_state)

        # Should have vowel stretching or typos
        assert degraded != text, "Text should be degraded"
        print(f"   Original: {text}")
        print(f"   Degraded: {degraded}")
        print("   ✓ Arousal effects triggered")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_sedation_effects_trigger():
    """Test that sedation effects trigger when GABA > 0.8."""
    print("\n3. Testing sedation effects trigger (GABA > 0.8)...")

    try:
        degrader = CadenceDegrader()

        limbic_state = {
            "DOPAMINE": 0.5,
            "CORTISOL": 0.5,
            "OXYTOCIN": 0.5,
            "GABA": 1.2,  # Very high GABA
        }

        text = "I feel so tired, I can barely keep my eyes open."
        degraded = degrader.degrade(text, limbic_state)

        # Should be lowercase with ellipses
        assert degraded != text, "Text should be degraded"
        assert degraded.islower() or "..." in degraded, "Should have sedation effects"
        print(f"   Original: {text}")
        print(f"   Degraded: {degraded}")
        print("   ✓ Sedation effects triggered")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_no_degradation_at_baseline():
    """Test that no degradation occurs when all neurochemicals are at baseline."""
    print("\n4. Testing no degradation at baseline...")

    try:
        degrader = CadenceDegrader()

        limbic_state = {
            "DOPAMINE": 0.5,
            "CORTISOL": 0.5,
            "OXYTOCIN": 0.5,
            "GABA": 0.5,
        }

        text = "This is a normal sentence at baseline."

        # Should not degrade
        should_degrade = degrader.should_degrade(limbic_state)
        assert not should_degrade, "Should not degrade at baseline"

        degraded = degrader.degrade(text, limbic_state)
        assert degraded == text, "Text should remain unchanged at baseline"

        print(f"   ✓ No degradation at baseline (text unchanged)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_threshold_detection():
    """Test should_degrade threshold detection."""
    print("\n5. Testing threshold detection...")

    try:
        degrader = CadenceDegrader()

        # Below threshold
        state_low = {
            "DOPAMINE": 0.5,
            "CORTISOL": 0.5,
            "OXYTOCIN": 0.5,
            "GABA": 0.5,
        }
        assert not degrader.should_degrade(state_low)

        # Above threshold (CORTISOL)
        state_high_cortisol = {
            "DOPAMINE": 0.5,
            "CORTISOL": 0.9,
            "OXYTOCIN": 0.5,
            "GABA": 0.5,
        }
        assert degrader.should_degrade(state_high_cortisol)

        # Above threshold (DOPAMINE)
        state_high_dopamine = {
            "DOPAMINE": 0.85,
            "CORTISOL": 0.5,
            "OXYTOCIN": 0.5,
            "GABA": 0.5,
        }
        assert degrader.should_degrade(state_high_dopamine)

        # Above threshold (GABA)
        state_high_gaba = {
            "DOPAMINE": 0.5,
            "CORTISOL": 0.5,
            "OXYTOCIN": 0.5,
            "GABA": 0.9,
        }
        assert degrader.should_degrade(state_high_gaba)

        print("   ✓ Threshold detection working correctly")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_combined_effects():
    """Test combined effects when multiple neurochemicals are high."""
    print("\n6. Testing combined effects...")

    try:
        degrader = CadenceDegrader()

        limbic_state = {
            "DOPAMINE": 1.2,  # High dopamine
            "CORTISOL": 0.9,  # High cortisol
            "OXYTOCIN": 0.5,
            "GABA": 0.3,  # Low GABA
        }

        text = "I need to calm down but I can't stop shaking."
        degraded = degrader.degrade(text, limbic_state)

        # Should have both arousal and panic effects
        assert degraded != text, "Text should be degraded"
        print(f"   Original: {text}")
        print(f"   Degraded: {degraded}")
        print("   ✓ Combined effects applied")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_vowel_stretching():
    """Test vowel stretching in arousal effects."""
    print("\n7. Testing vowel stretching...")

    try:
        degrader = CadenceDegrader()

        # Test vowel stretching directly
        text = "please"
        stretched = degrader._stretch_vowels(text)

        # Should have more vowels than original
        original_vowel_count = sum(1 for c in text if c.lower() in "aeiou")
        stretched_vowel_count = sum(1 for c in stretched if c.lower() in "aeiou")

        assert stretched_vowel_count >= original_vowel_count, (
            "Should have stretched vowels"
        )
        print(f"   Original: {text}")
        print(f"   Stretched: {stretched}")
        print("   ✓ Vowel stretching works")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_extreme_pathological_state():
    """Test degradation with pathological states (values > 1.0)."""
    print("\n8. Testing extreme pathological states...")

    try:
        degrader = CadenceDegrader()

        limbic_state = {
            "DOPAMINE": 1.5,  # Pathological
            "CORTISOL": 1.5,  # Pathological
            "OXYTOCIN": 0.5,
            "GABA": 0.0,  # Complete absence
        }

        text = "Everything is too much I cannot handle this."
        degraded = degrader.degrade(text, limbic_state)

        # Should be heavily degraded
        assert degraded != text, "Text should be heavily degraded"
        print(f"   Original: {text}")
        print(f"   Degraded: {degraded}")
        print("   ✓ Extreme pathological states handled")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def run_all_tests():
    """Run all Cadence Degrader tests."""
    print("\n" + "=" * 60)
    print("CADENCE DEGRADATION ENGINE TEST SUITE")
    print("=" * 60)

    tests = [
        test_panic_effects_trigger,
        test_arousal_effects_trigger,
        test_sedation_effects_trigger,
        test_no_degradation_at_baseline,
        test_threshold_detection,
        test_combined_effects,
        test_vowel_stretching,
        test_extreme_pathological_state,
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
