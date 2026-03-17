"""
Persona Manager - Handles persona switching and ensemble mode management.

This module manages active persona state for users, supporting both single-persona
mode (legacy) and ensemble mode (multiple personas active simultaneously).

Extracted from AgentCore during RDSSC Phase 4.
RDSSC Phase 3: Refactored to use UserStateManager directly instead of through MemoryMatrix.
"""

from typing import List, Optional

from core.features.roleplay.persona import PersonaLoader, PersonaCartridge
from core.features.roleplay.user_state import UserStateManager
from core.logger import get_logger


class PersonaManager:
    """Manages active persona state and ensemble mode for users."""

    def __init__(self, persona_loader: PersonaLoader, user_state: UserStateManager):
        """
        Initialize persona manager.

        Args:
            persona_loader: PersonaLoader instance for loading persona cartridges
            user_state: UserStateManager instance for storing active persona state
        """
        self.persona_loader = persona_loader
        self.user_state = user_state

    def get_active_personas(self, user_id: str) -> List[PersonaCartridge]:
        """
        Get all currently active personas for a user (Ensemble Mode).

        Args:
            user_id: Unique user identifier (platform-agnostic)

        Returns:
            List of PersonaCartridge objects (empty if none active)
        """
        persona_ids = self.user_state.get_active_personas(user_id)

        personas = []
        for persona_id in persona_ids:
            persona = self.persona_loader.get_persona(persona_id)
            if persona:
                personas.append(persona)

        return personas

    def get_active_persona(self, user_id: str) -> Optional[PersonaCartridge]:
        """
        Get the first active persona for a user (legacy method for backwards compatibility).

        Args:
            user_id: Unique user identifier (platform-agnostic)

        Returns:
            PersonaCartridge if user has an active persona, None otherwise
        """
        personas = self.get_active_personas(user_id)
        return personas[0] if personas else None

    def add_active_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Add a persona to the active ensemble (appends, does not replace).

        Args:
            user_id: Unique user identifier
            persona_id: The persona to add

        Returns:
            True if successful, False if persona doesn't exist
        """
        # Verify persona exists
        persona = self.persona_loader.get_persona(persona_id)
        if not persona:
            return False

        # Add to active ensemble
        self.user_state.add_active_persona(user_id, persona_id)
        return True

    def remove_active_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Remove a specific persona from the active ensemble.

        Args:
            user_id: Unique user identifier
            persona_id: The persona to remove

        Returns:
            True if persona was removed, False if it wasn't active
        """
        return self.user_state.remove_active_persona(user_id, persona_id)

    def clear_active_personas(self, user_id: str) -> None:
        """
        Clear all active personas for a user.

        Args:
            user_id: Unique user identifier
        """
        self.user_state.clear_active_personas(user_id)

    def switch_persona(self, user_id: str, persona_id: str) -> bool:
        """
        Switch a user's active persona (legacy method - clears other personas).

        Args:
            user_id: Unique user identifier
            persona_id: The persona to switch to

        Returns:
            True if successful, False if persona doesn't exist
        """
        logger = get_logger()
        logger.debug(
            f"PersonaManager.switch_persona called: user_id={user_id}, persona_id={persona_id}"
        )

        # Verify persona exists
        logger.debug(f"Loading persona '{persona_id}'...")
        persona = self.persona_loader.get_persona(persona_id)
        logger.debug(f"Persona loaded: {persona.name if persona else None}")
        if not persona:
            logger.debug("Persona not found, returning False")
            return False

        # Update user state (sets single persona, clearing others)
        logger.debug("Setting active persona in user_state...")
        self.user_state.set_active_persona(user_id, persona_id)
        logger.debug("Active persona set, returning True")
        return True

    def list_personas(self) -> List[str]:
        """
        List all available persona IDs.

        Returns:
            List of persona_id strings
        """
        return self.persona_loader.list_available_personas()
