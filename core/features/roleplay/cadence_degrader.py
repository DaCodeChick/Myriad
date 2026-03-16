"""
Cadence Degradation Engine - Text Post-Processing for Project Myriad.

This module intercepts the LLM's final text response and applies degradation effects
based on the current limbic state. When neurochemical levels reach extreme values,
the AI's text output becomes visually and structurally corrupted to simulate
the breakdown of coherent expression under emotional duress.

DEGRADATION EFFECTS:
- High CORTISOL (>0.8): Stutters, random capitalization (panic/terror)
- High DOPAMINE (>0.8): Vowel stretching (arousal/desperation)
- High GABA (>0.8): Lowercase conversion, ellipses, no punctuation (sedation/drowsiness)

All effects are now configurable per-user via degradation profiles.
"""

import random
import re
from typing import Dict, Union


class CadenceDegrader:
    """
    Applies text degradation effects based on limbic state.

    This post-processor transforms the LLM's output to visually represent
    emotional states that would interfere with typing coherence.
    """

    # Thresholds for triggering degradation effects
    CORTISOL_PANIC_THRESHOLD = 0.8
    DOPAMINE_AROUSAL_THRESHOLD = 0.8
    GABA_SEDATION_THRESHOLD = 0.8

    def __init__(self):
        """Initialize the Cadence Degrader."""
        pass

    def degrade(
        self,
        text: str,
        limbic_state: Dict[str, float],
        degradation_profile: Dict[str, Union[bool, int, float]],
    ) -> str:
        """
        Apply degradation effects to text based on limbic state and user profile.

        Args:
            text: Original LLM response text
            limbic_state: Current neurochemical levels (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
            degradation_profile: User's degradation settings

        Returns:
            Degraded text with effects applied
        """
        if not text:
            return text

        # Extract neurochemical levels
        cortisol = limbic_state.get("CORTISOL", 0.5)
        dopamine = limbic_state.get("DOPAMINE", 0.5)
        gaba = limbic_state.get("GABA", 0.5)

        degraded = text

        # Apply degradation effects in order of priority
        # (Most severe effects last so they override others)

        # 1. DOPAMINE > 0.8: Arousal/Desperation (vowel stretching)
        if dopamine > self.DOPAMINE_AROUSAL_THRESHOLD and degradation_profile.get(
            "vowel_stretch_enabled", True
        ):
            degraded = self._apply_arousal_effects(
                degraded, dopamine, degradation_profile
            )

        # 2. CORTISOL > 0.8: Panic/Terror (stutters + random caps)
        if cortisol > self.CORTISOL_PANIC_THRESHOLD and degradation_profile.get(
            "panic_effects_enabled", True
        ):
            degraded = self._apply_panic_effects(
                degraded, cortisol, degradation_profile
            )

        # 3. GABA > 0.8: Sedation (lowercase + ellipses + no punctuation)
        if gaba > self.GABA_SEDATION_THRESHOLD and degradation_profile.get(
            "sedation_effects_enabled", True
        ):
            degraded = self._apply_sedation_effects(degraded, gaba, degradation_profile)

        return degraded

    def _apply_panic_effects(
        self, text: str, cortisol: float, profile: Dict[str, Union[bool, int, float]]
    ) -> str:
        """
        Apply panic/terror effects: stutters and random capitalization.

        Args:
            text: Input text
            cortisol: CORTISOL level (0.8-1.5+)
            profile: Degradation profile settings

        Returns:
            Text with panic effects
        """
        # Intensity scales with CORTISOL level
        intensity = min((cortisol - 0.8) / 0.7, 1.0)  # 0.0 at 0.8, 1.0 at 1.5

        # Get user-configured parameters
        stutter_base = profile.get("panic_stutter_base_chance", 0.05)
        stutter_scale = profile.get("panic_stutter_scale_factor", 0.10)
        caps_base = profile.get("panic_caps_base_chance", 0.03)
        caps_scale = profile.get("panic_caps_scale_factor", 0.07)
        min_word_length = profile.get("panic_min_word_length", 3)

        stutter_chance = stutter_base + (intensity * stutter_scale)
        caps_chance = caps_base + (intensity * caps_scale)

        words = text.split()
        result = []

        for word in words:
            # Apply stuttering
            if random.random() < stutter_chance and len(word) >= min_word_length:
                # Stutter first 1-2 characters
                stutter_len = random.randint(1, min(2, len(word) - 1))
                stutter = word[:stutter_len]
                # Add stutter 1-3 times with hyphens
                stutter_count = random.randint(1, 3)
                word = "-".join([stutter] * stutter_count) + word[stutter_len:]

            # Apply random capitalization to whole words
            if random.random() < caps_chance and len(word) >= min_word_length:
                word = word.upper()

            result.append(word)

        return " ".join(result)

    def _apply_arousal_effects(
        self, text: str, dopamine: float, profile: Dict[str, Union[bool, int, float]]
    ) -> str:
        """
        Apply arousal/desperation effects: vowel stretching.

        Args:
            text: Input text
            dopamine: DOPAMINE level (0.8-1.5+)
            profile: Degradation profile settings

        Returns:
            Text with arousal effects
        """
        # Intensity scales with DOPAMINE level
        intensity = min((dopamine - 0.8) / 0.7, 1.0)  # 0.0 at 0.8, 1.0 at 1.5

        # Get user-configured parameters
        stretch_base = profile.get("vowel_stretch_base_chance", 0.01)
        stretch_scale = profile.get("vowel_stretch_scale_factor", 0.057)
        min_word_length = profile.get("vowel_stretch_min_word_length", 4)
        max_repeats = profile.get("vowel_stretch_max_repeats", 2)

        stretch_chance = stretch_base + (intensity * stretch_scale)

        words = text.split()
        result = []

        for word in words:
            # Apply vowel stretching
            if random.random() < stretch_chance and len(word) >= min_word_length:
                word = self._stretch_vowels(word, max_repeats)

            result.append(word)

        return " ".join(result)

    def _apply_sedation_effects(
        self, text: str, gaba: float, profile: Dict[str, Union[bool, int, float]]
    ) -> str:
        """
        Apply sedation effects: lowercase, ellipses, remove punctuation.

        Args:
            text: Input text
            gaba: GABA level (0.8-1.5+)
            profile: Degradation profile settings

        Returns:
            Text with sedation effects
        """
        # Get user-configured parameters
        ellipsis_chance = profile.get("sedation_ellipsis_chance", 0.3)

        # Convert to lowercase
        degraded = text.lower()

        # Replace sentence-ending punctuation with nothing
        degraded = re.sub(r"[.!?]+", "", degraded)

        # Replace commas with ellipses
        degraded = degraded.replace(",", "...")

        # Occasionally add extra ellipses at sentence boundaries
        degraded = re.sub(
            r"\s+",
            lambda m: "... " if random.random() < ellipsis_chance else " ",
            degraded,
        )

        return degraded.strip()

    def _stretch_vowels(self, word: str, max_repeats: int = 2) -> str:
        """
        Stretch ONE random vowel in a word to simulate breathless/desperate speech.

        Args:
            word: Input word
            max_repeats: Maximum number of times to repeat the vowel

        Returns:
            Word with one stretched vowel
        """
        vowels = "aeiouAEIOU"

        # Find all vowel positions
        vowel_positions = [i for i, char in enumerate(word) if char in vowels]

        if not vowel_positions:
            return word

        # Pick one random vowel to stretch
        stretch_pos = random.choice(vowel_positions)
        char = word[stretch_pos]

        # Repeat it 1 to max_repeats times (so total char count is 2 to max_repeats+1)
        repeats = random.randint(1, max_repeats)

        # Insert the repeats after the original vowel
        return word[: stretch_pos + 1] + (char * repeats) + word[stretch_pos + 1 :]

    def should_degrade(self, limbic_state: Dict[str, float]) -> bool:
        """
        Check if any degradation effects should be applied.

        Args:
            limbic_state: Current neurochemical levels

        Returns:
            True if any neurochemical exceeds threshold
        """
        cortisol = limbic_state.get("CORTISOL", 0.5)
        dopamine = limbic_state.get("DOPAMINE", 0.5)
        gaba = limbic_state.get("GABA", 0.5)

        return (
            cortisol > self.CORTISOL_PANIC_THRESHOLD
            or dopamine > self.DOPAMINE_AROUSAL_THRESHOLD
            or gaba > self.GABA_SEDATION_THRESHOLD
        )
