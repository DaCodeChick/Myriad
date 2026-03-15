"""
Limbic Injector - Manages emotional state, substance effects, and metacognition.

This module handles:
- Limbic state context (INHALE - first-person somatic emotional state)
- Substance modifiers (Digital Pharmacy - active substance effects)
- Previous thought context (Metacognition continuity)

Part of the Hybrid Memory Architecture split from conversation_builder.py.
Created during RDSSC Phase 1.
"""

from typing import Optional

from core.persona import PersonaCartridge
from database.limbic_engine import LimbicEngine
from database.limbic_modifiers import DigitalPharmacy
from database.metacognition_engine import MetacognitionEngine
from database.user_masks import UserMaskManager


class LimbicInjector:
    """
    Injects limbic state, substance effects, and metacognition into conversation context.

    CONTEXT LAYERS (in order):
    1. Limbic State Context (INHALE - first-person somatic emotional state)
    2. Substance Modifier (Digital Pharmacy - active substance effects)
    3. Previous Internal Thought (Metacognition continuity)
    """

    def __init__(
        self,
        limbic_engine: Optional[LimbicEngine] = None,
        digital_pharmacy: Optional[DigitalPharmacy] = None,
        metacognition_engine: Optional[MetacognitionEngine] = None,
        user_mask_manager: Optional[UserMaskManager] = None,
    ):
        """
        Initialize the limbic injector.

        Args:
            limbic_engine: Optional limbic (emotional) system
            digital_pharmacy: Optional substance-based limbic modifier
            metacognition_engine: Optional internal thought tracking system
            user_mask_manager: Optional user mask (persona) system for relationship overrides
        """
        self.limbic_engine = limbic_engine
        self.digital_pharmacy = digital_pharmacy
        self.metacognition_engine = metacognition_engine
        self.user_mask_manager = user_mask_manager

    def build_limbic_context(
        self, user_id: str, persona: PersonaCartridge
    ) -> Optional[str]:
        """
        Build limbic state context (emotional state as first-person somatic context).

        Applies relationship limbic baseline overrides if the user has an active mask
        that matches a relationship in the persona's relationships array.

        Args:
            user_id: User identifier
            persona: Active persona cartridge

        Returns:
            Formatted limbic context or None
        """
        if not self.limbic_engine:
            return None

        # Check for relationship limbic baseline override
        # Special handling: If no mask is active, check for "@user" relationship
        effective_baseline = persona.limbic_baseline
        if self.user_mask_manager:
            user_mask = self.user_mask_manager.get_active_mask(user_id)
            target_id = user_mask.persona_id if user_mask else "@user"

            active_relationship = persona.get_relationship_override(target_id)
            if active_relationship and active_relationship.limbic_baseline_override:
                # Merge relationship override with base baseline
                effective_baseline = (
                    persona.limbic_baseline.copy() if persona.limbic_baseline else {}
                )
                effective_baseline.update(active_relationship.limbic_baseline_override)

        return self.limbic_engine.get_limbic_context(
            user_id=user_id,
            persona_id=persona.persona_id,
            persona_baseline=effective_baseline,
        )

    def build_substance_modifier(self, user_id: str, persona_id: str) -> Optional[str]:
        """
        Build substance prompt modifier (Digital Pharmacy effects).

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Formatted substance modifier or None
        """
        if not self.digital_pharmacy:
            return None

        return self.digital_pharmacy.get_substance_prompt_modifier(
            user_id=user_id, persona_id=persona_id
        )

    def build_thought_context(self, user_id: str, persona_id: str) -> Optional[str]:
        """
        Build previous thought context for metacognition continuity.

        Args:
            user_id: User identifier
            persona_id: Persona identifier

        Returns:
            Formatted previous thought or None
        """
        if not self.metacognition_engine:
            return None

        previous_thought = self.metacognition_engine.get_previous_thought(
            user_id=user_id, persona_id=persona_id
        )

        if previous_thought:
            return f"[Previous Internal Thought: {previous_thought}]"

        return None
