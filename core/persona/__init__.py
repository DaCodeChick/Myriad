"""
Persona management package for Project Myriad.

This package handles loading, caching, and managing persona cartridges with
hot-swappable personality configurations.
"""

from core.persona.persona_models import PersonaCartridge, PersonaRelationship
from core.persona.persona_manager import PersonaLoader

__all__ = ["PersonaCartridge", "PersonaRelationship", "PersonaLoader"]
