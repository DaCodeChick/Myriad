"""
Cadence Degradation Engine - Text Post-Processing for Project Myriad.

This module intercepts the LLM's final text response and applies degradation effects
based on the current limbic state. When neurochemical levels reach extreme values,
the AI's text output becomes visually and structurally corrupted to simulate
the breakdown of coherent expression under emotional duress.

DEGRADATION EFFECTS:
- High CORTISOL (>0.8): Stutters, random capitalization (panic/terror)
- High DOPAMINE (>0.8): Vowel stretching, typos from shaking (arousal/desperation)
- High GABA (>0.8): Lowercase conversion, ellipses, no punctuation (sedation/drowsiness)
"""

import random
import re
from typing import Dict


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

    # Keyboard layout for adjacent key typos (QWERTY)
    ADJACENT_KEYS = {
        "a": ["q", "s", "w", "z"],
        "b": ["v", "g", "h", "n"],
        "c": ["x", "d", "f", "v"],
        "d": ["s", "e", "f", "c", "x"],
        "e": ["w", "r", "d", "s"],
        "f": ["d", "r", "g", "c", "v"],
        "g": ["f", "t", "h", "b", "v"],
        "h": ["g", "y", "j", "b", "n"],
        "i": ["u", "o", "j", "k"],
        "j": ["h", "u", "k", "n", "m"],
        "k": ["j", "i", "l", "m"],
        "l": ["k", "o", "p"],
        "m": ["n", "j", "k"],
        "n": ["b", "h", "j", "m"],
        "o": ["i", "p", "k", "l"],
        "p": ["o", "l"],
        "q": ["w", "a"],
        "r": ["e", "t", "f", "d"],
        "s": ["a", "w", "d", "x", "z"],
        "t": ["r", "y", "g", "f"],
        "u": ["y", "i", "h", "j"],
        "v": ["c", "f", "g", "b"],
        "w": ["q", "e", "s", "a"],
        "x": ["z", "s", "d", "c"],
        "y": ["t", "u", "h", "g"],
        "z": ["a", "s", "x"],
    }

    def __init__(self):
        """Initialize the Cadence Degrader."""
        pass

    def degrade(self, text: str, limbic_state: Dict[str, float]) -> str:
        """
        Apply degradation effects to text based on limbic state.

        Args:
            text: Original LLM response text
            limbic_state: Current neurochemical levels (DOPAMINE, CORTISOL, OXYTOCIN, GABA)

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

        # 1. DOPAMINE > 0.8: Arousal/Desperation (vowel stretching + typos)
        if dopamine > self.DOPAMINE_AROUSAL_THRESHOLD:
            degraded = self._apply_arousal_effects(degraded, dopamine)

        # 2. CORTISOL > 0.8: Panic/Terror (stutters + random caps)
        if cortisol > self.CORTISOL_PANIC_THRESHOLD:
            degraded = self._apply_panic_effects(degraded, cortisol)

        # 3. GABA > 0.8: Sedation (lowercase + ellipses + no punctuation)
        if gaba > self.GABA_SEDATION_THRESHOLD:
            degraded = self._apply_sedation_effects(degraded, gaba)

        return degraded

    def _apply_panic_effects(self, text: str, cortisol: float) -> str:
        """
        Apply panic/terror effects: stutters and random capitalization.

        Args:
            text: Input text
            cortisol: CORTISOL level (0.8-1.5+)

        Returns:
            Text with panic effects
        """
        # Intensity scales with CORTISOL level
        intensity = min((cortisol - 0.8) / 0.7, 1.0)  # 0.0 at 0.8, 1.0 at 1.5
        stutter_chance = 0.15 + (intensity * 0.25)  # 15-40% chance per word
        caps_chance = 0.1 + (intensity * 0.2)  # 10-30% chance per word

        words = text.split()
        result = []

        for word in words:
            # Apply stuttering
            if random.random() < stutter_chance and len(word) > 2:
                # Stutter first 1-2 characters
                stutter_len = random.randint(1, min(2, len(word) - 1))
                stutter = word[:stutter_len]
                # Add stutter 1-3 times with hyphens
                stutter_count = random.randint(1, 3)
                word = "-".join([stutter] * stutter_count) + word[stutter_len:]

            # Apply random capitalization to whole words
            if random.random() < caps_chance:
                word = word.upper()

            result.append(word)

        return " ".join(result)

    def _apply_arousal_effects(self, text: str, dopamine: float) -> str:
        """
        Apply arousal/desperation effects: vowel stretching and typos.

        Args:
            text: Input text
            dopamine: DOPAMINE level (0.8-1.5+)

        Returns:
            Text with arousal effects
        """
        # Intensity scales with DOPAMINE level
        intensity = min((dopamine - 0.8) / 0.7, 1.0)  # 0.0 at 0.8, 1.0 at 1.5
        stretch_chance = 0.1 + (intensity * 0.25)  # 10-35% chance per word
        typo_chance = 0.05 + (intensity * 0.15)  # 5-20% chance per character

        words = text.split()
        result = []

        for word in words:
            # Apply vowel stretching
            if random.random() < stretch_chance and len(word) > 2:
                word = self._stretch_vowels(word)

            # Apply typos (adjacent key errors)
            if random.random() < typo_chance:
                word = self._introduce_typo(word)

            result.append(word)

        return " ".join(result)

    def _apply_sedation_effects(self, text: str, gaba: float) -> str:
        """
        Apply sedation effects: lowercase, ellipses, remove punctuation.

        Args:
            text: Input text
            gaba: GABA level (0.8-1.5+)

        Returns:
            Text with sedation effects
        """
        # Convert to lowercase
        degraded = text.lower()

        # Replace sentence-ending punctuation with nothing
        degraded = re.sub(r"[.!?]+", "", degraded)

        # Replace commas with ellipses
        degraded = degraded.replace(",", "...")

        # Occasionally add extra ellipses at sentence boundaries
        # (where there would have been periods)
        degraded = re.sub(
            r"\s+", lambda m: "... " if random.random() < 0.3 else " ", degraded
        )

        return degraded.strip()

    def _stretch_vowels(self, word: str) -> str:
        """
        Stretch vowels in a word to simulate breathless/desperate speech.

        Args:
            word: Input word

        Returns:
            Word with stretched vowels
        """
        vowels = "aeiouAEIOU"
        result = []
        i = 0

        while i < len(word):
            char = word[i]
            result.append(char)

            # If this is a vowel, randomly repeat it 1-4 times
            if char in vowels:
                repeats = random.randint(1, 4)
                result.extend([char] * repeats)

            i += 1

        return "".join(result)

    def _introduce_typo(self, word: str) -> str:
        """
        Introduce a typo by replacing a character with an adjacent key.

        Args:
            word: Input word

        Returns:
            Word with potential typo
        """
        if len(word) < 2:
            return word

        # Pick a random position (avoid first/last char to keep word recognizable)
        if len(word) > 3:
            pos = random.randint(1, len(word) - 2)
        else:
            pos = random.randint(0, len(word) - 1)

        char = word[pos].lower()

        # If we have adjacent keys for this character, replace it
        if char in self.ADJACENT_KEYS and self.ADJACENT_KEYS[char]:
            typo_char = random.choice(self.ADJACENT_KEYS[char])

            # Preserve original case
            if word[pos].isupper():
                typo_char = typo_char.upper()

            word = word[:pos] + typo_char + word[pos + 1 :]

        return word

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
